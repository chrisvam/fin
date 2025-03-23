from collections import deque

Single=0
Married=1

# from 1871 thru 2024 from https://www.multpl.com/inflation-adjusted-s-p-500/table/by-year
SandP_InflationCorrectedReturns_Since1871=[
    4948.65,4205.59,5167.98,4607.21,4036.85,3290.63,3575.46,2976.21,2572.57,
    2756.84,2474.87,2042.21,1822.76,1850.18,1647.21,1302.29,2075.01,2235.07,
    2048.49,1968.01,1942.60,1566.22,2045.24,2423.13,2682.87,2414.47,1893.76,
    1529.89,1264.14,983.34,1027.74,969.56,957.11,768.19,847.71,748.66,687.78,755.61,
    603.46,516.70,518.75,468.71,395.15,485.63,452.82,463.76,458.72,563.66,553.41,
    442.42,655.18,882.92,798.43,746.21,758.96,910.18,885.38,815.42,932.23,876.85,785.95,
    679.86,731.38,636.62,629.16,609.27,456.74,522.89,523.33,423.56,300.67,312.66,289.98,
    265.27,228.18,203.31,198.78,224.73,314.53,240.75,216.34,189.66,180.69,237.69,281.10,
    283.63,253.02,396.30,316.75,216.30,253.66,174.60,184.38,319.27,403.31,461.83,321.89,
    243.25,224.50,194.28,162.14,168.29,137.22,118.88,145.34,151.13,163.60,259.84,284.99,
    235.27,265.89,301.46,317.32,319.05,323.45,321.94,251.28,343.16,370.18,316.17,256.29,
    310.33,326.52,291.30,245.29,285.72,232.77,207.20,203.67,205.49,200.34,225.59,238.79,
    197.12,224.58,208.33,201.53,221.85,206.74,162.67,178.28,184.75,184.74,208.75,162.49,
    137.35,111.86,103.08,130.58,125.30,119.67,125.45,122.05,113.20]
SandP_InflationCorrectedReturns_Since1871.reverse()

RMDTable = ((75,24.6), (76,23.7), (77,22.9), (78,22.0), (79,21.1), (80,20.2),
            (81,19.4), (82,18.5), (83,17.7), (84,16.8), (85,16.0), (86,15.2),
            (87,14.4), (88,13.7), (89,12.9), (90,12.2), (91,11.5), (92,10.8),
            (93,10.1), (94,9.5),  (95,8.9),  (96,8.4),  (99,6.8,), (100,6.4),
            (101,6.0), (102,5.6), (103,5.2), (104,4.9), (105,4.6), (106,4.3),
            (107,4.1), (108,3.9), (109,3.7), (110,3.5), (111,3.4), (112,3.3),
            (113,3.1), (114,3.0), (115,2.9), (116,2.8), (117,2.7), (118,2.5),
            (119,2.3), (120,2.0))

class FedTax:
    # tax calculation requires brackets/rates in descending order
    brackets = ((250.525,197.300,103.350,48.475,11.925,0), # single
                (501.050,394.600,206.700,96.950,23.850,0)) # married
    rates = (0.35,0.32,0.24,0.22,0.12,0.10)
    deduction=(14.6,29.2) # single/married

class StateTax: # for california
    # tax calculation requires brackets/rates in descending order
    brackets = ((721.315,432.788,360.660,70.607,55.867,40.246,25.500,10.757,0),
                (1442.629,865.575,721.319,141.213,111.733,80.491,50.999,21.513,0))
    rates = (0.123,0.113,0.103,0.093,0.08,0.06,0.04,0.02,0.01)
    deduction = (5.54,11.08) # single/married

class Person:
    def __init__(self, dictionary):
        for k, v in dictionary.items():
            setattr(self, k, v)

class Model:
    def __init__(self, dictionary):
        for k, v in dictionary.items():
            setattr(self, k, v)
    def alive(self):
        return len(self.people)
    def newYear(self):
        self.year+=1
        removeIndices = []
        for i,p in enumerate(self.people):
            p.age+=1
            if p.age==p.deathAge: removeIndices.append(i)
        for i in removeIndices: del self.people[i]

class Balances:
    def __init__(self,model):
        self.model = model
        self.taxable = model.taxableStart
        self.pretax = model.pretaxStart
        self.roth = model.rothStart
        self.people = model.people
        self.pretaxWithdrawn=0 # hack for computing pretax taxes next year
        self.incomeLookback=deque(maxlen=3)
        self.marketReturnsIndex = self.model.SandPReturnsStartYear-1871

    def update(self):
        if self.model.SandPReturnsStartYear > 0 and \
            self.marketReturnsIndex+1<len(SandP_InflationCorrectedReturns_Since1871)-1 :
            # use historical inflation-corrected market return data
            lastYear = SandP_InflationCorrectedReturns_Since1871[self.marketReturnsIndex]
            thisYear = SandP_InflationCorrectedReturns_Since1871[self.marketReturnsIndex+1]
            self.model.marketReturn = (thisYear/lastYear)-1
            self.marketReturnsIndex+=1 # move forward a year
        else: # use an average number
            self.model.marketReturn = self.model.marketReturnAvg
        if len(self.people)==1: self.filingStatus=Single
        else: self.filingStatus=Married

        self.income,self.socsecIncome = self.calcIncome()
        # how much are we contributing to roth/pretax
        rothContrib,pretaxContrib = self.calcRothAndPretaxContrib(self.income)
        self.rmd = self.calcRMD()
        self.pretax-=self.rmd
        # hack: add in last last year's pretax withdrawal to this year's income
        # this avoids recursion loops
        self.income+=(self.rmd+self.pretaxWithdrawn)
        self.totincome = self.income+self.socsecIncome

        # only federal taxes socsec
        socsecTaxable = self.calcSocsecTaxable(self.income,self.socsecIncome)
        capgains = self.taxable*self.model.marketReturn
        taxableIncome = self.income-pretaxContrib
        fedTaxableIncome = taxableIncome+socsecTaxable-FedTax.deduction[self.filingStatus]
        # california taxes capital gains as income, but not socsec
        stateTaxableIncome  = taxableIncome+capgains-StateTax.deduction[self.filingStatus]

        # optional roth conversion
        convertBracket=self.model.rothConvertBracket
        self.convert=0
        if convertBracket>=0:
            self.convert=max(min(FedTax.brackets[self.filingStatus][convertBracket]-fedTaxableIncome,self.pretax),0) # max out this bracket
            if self.convert>0:
                fedTaxableIncome+=self.convert # pay taxes on conversion
                stateTaxableIncome+=self.convert # pay taxes on conversion
                self.roth+=self.convert # add to roth
                self.pretax-=self.convert # remove from pretax
        self.incomeLookback.append(fedTaxableIncome) # simplification: this is not magi
        self.fedtax = self.calcTax(fedTaxableIncome,FedTax) \
            + self.calcCapgainsTax(self.income,capgains)
        self.statetax = self.calcTax(stateTaxableIncome,StateTax)
        # update totals with our contributions
        tottax = self.fedtax+self.statetax

        self.pretax += pretaxContrib
        self.roth += rothContrib
        self.health = self.calcHealth(self.incomeLookback[0])
        self.totExpenses = rothContrib+pretaxContrib+tottax+self.model.expenses+self.health
        # hack: will compute taxes on this next year
        self.pretaxWithdrawn=0
        netcash = self.income - self.totExpenses
        if netcash >= 0: # don't need to withdraw, put excess in taxable
            self.taxable += self.income-self.totExpenses
        else: # we have to withdraw
            # take from taxable first
            if self.taxable+netcash>0: self.taxable+=netcash
            else: # not enough in taxable, try pretax
                netcash+=self.taxable # drain taxable
                self.taxable=0
                # is there enough in pretax?
                if self.pretax+netcash>0:
                    self.pretaxWithdrawn= -netcash
                    self.pretax+=netcash
                else: # not enough in pretax, try roth
                    netcash+=self.pretax # drain pretax
                    self.pretaxWithdrawn= self.pretax
                    self.pretax=0
                    if self.roth+netcash>0: self.roth+=netcash
                    else:
                        print('*** bankrupt ***')
                        import sys
                        sys.exit(-1)
                    
        # market returns
        self.pretax*=(1+self.model.marketReturn)
        self.roth*=(1+self.model.marketReturn)
        self.taxable*=(1+self.model.marketReturn)

    # cpo doesn't understand this, but the results from this chatGPT
    # generated code seem to agree with the calculator here:
    # https://www.covisum.com/resources/taxable-social-security-calculator
    # another interesting paper here:
    # https://www.financialplanningassociation.org/sites/default/files/2020-09/July2018_Contribution_Reichenstein.pdf
    def calcSocsecTaxable(self, income, socsecIncome):
        # simplifying assumption: assume tax-exempt interest is 0
        provisional_income = income + 0.5 * socsecIncome
    
        if self.filingStatus == Single:
            base1, base2 = 25000, 34000
        elif self.filingStatus == Married:
            base1, base2 = 32000, 44000
    
        if provisional_income <= base1:
            taxable_ssi = 0
        elif provisional_income <= base2:
            taxable_ssi = 0.5 * (provisional_income - base1)
        else:
            taxable_ssi = 0.85 * (provisional_income - base2) + 0.5 * (base2 - base1)
            taxable_ssi = min(taxable_ssi, 0.85 * socsecIncome)
        
        return taxable_ssi
        
    # courtesy of chatGPT
    def calcIrmaa(self,magi):
        # this income "looks back" 2 years
        # subject to change, so check the latest thresholds
        irmaa_thresholds = (((91, 114, 68, 12.40),
                             (114, 142, 170.10, 31.90),
                             (142, 170, 272.20, 51.40),
                             (170, 500, 374.20, 70.90),
                             (500, float('inf'), 408.20, 77.90)),
                            ((182, 228, 68, 12.40),
                             (228, 284, 170.10, 31.90),
                             (284, 340, 272.20, 51.40),
                             (340, 750, 374.20, 70.90),
                             (750, float('inf'), 408.20, 77.90)))

        for threshold in irmaa_thresholds[self.filingStatus]:
            low, high, part_b, part_d = threshold
            if low < magi <= high:
                return 12*part_b/1000 + 12*part_d/1000 # convert to annual kilobucks 
    
        return 0

    def calcRothAndPretaxContrib(self,income):
        roth=0
        pretax=0
        for p in self.people:
            if p.age < p.retireAge:
                roth+=income*p.rothFraction
                pretax+=income*p.pretaxFraction
        return roth,pretax

    def calcHealth(self,income):
        health = 0
        for p in self.people:
            if p.age >= p.retireAge:
                health+=(.185*12) # part B
                health+=(.145*12) # part D, approximate
                health+=(.2*12)   # part G supplemental insurance, approximate
                health+=self.calcIrmaa(income)
        return health

    def calcRMD(self):
        # simplification: assume both spouses are same age so
        # we don't have to divide up pretax balances
        age = self.people[0].age
        if age>=75:
            assert age==RMDTable[age-75][0]
            yearsToLive = RMDTable[age-75][1]
            return self.pretax/yearsToLive
        else: return 0

    def calcIncome(self):
        income = 0
        socsecIncome = 0
        for p in self.people:
            if p.age < p.retireAge:
                income+=p.salary
                socsecSalary = min(p.salary,176.1)
                income -= 0.062*socsecSalary # remove socsec payroll taxes
            if p.age >= p.socsecAge: socsecIncome+=p.socsecIncome
        return income,socsecIncome

    def calcTax(self,income,taxtype):
        tax=0
        # depends on the tax bracket table being in descending order
        for rate,bracket in zip(taxtype.rates,taxtype.brackets[self.filingStatus]):
            if income>=bracket:
                amountInBracket = income-bracket
                tax += rate*amountInBracket
                income -= amountInBracket
                #print('***',income,rate,brkt,amountInBracket,taxableIncome,filingStatus)
        return tax

    # see calculator here: https://www.nerdwallet.com/article/taxes/capital-gains-tax-rates
    def calcCapgainsTax(self,income,ltcg):
        if self.filingStatus==Married:
            threshold_0 = 89.250    # up to here, LTCG is taxed at 0%
            threshold_15 = 553.850  # up to here, LTCG (after the 0% portion) is taxed at 15%
        else:
            threshold_0 = 44.625    # up to here, LTCG is taxed at 0%
            threshold_15 = 492.300  # up to here, LTCG (after the 0% portion) is taxed at 15%

        # Determine how much of the LTCG falls into the 0% bracket.
        # If ordinary income is below the threshold, some LTCG will be "covered"
        # by the 0% zone.
        available_0_rate = max(0, threshold_0 - income)
        portion_0 = min(ltcg, available_0_rate)

        # Remaining LTCG after the 0% portion:
        remaining_ltcg = ltcg - portion_0

        # Next, determine how much LTCG falls into the 15% bracket.
        # The 15% bracket starts at the greater of (income, threshold_0)
        # and goes up to threshold_15.
        current_income_after_0 = income + portion_0
        available_15_rate = max(0, threshold_15 - current_income_after_0)
        portion_15 = min(remaining_ltcg, available_15_rate)

        # Any remaining LTCG falls into the 20% bracket.
        portion_20 = remaining_ltcg - portion_15

        tax = 0.15 * portion_15 + 0.20 * portion_20
        return tax
        
def printYear(year,people,balances):
    print(f"{year} {balances.totincome:4.0f} {balances.totExpenses:4.0f} {balances.taxable:5.0f} {balances.roth:5.0f} {balances.pretax:5.0f} {balances.fedtax:4.0f} {balances.statetax:4.0f} {balances.rmd:4.0f} {balances.pretaxWithdrawn:4.0f} {balances.convert:4.0f} {balances.health:4.0f} {balances.model.marketReturn:5.2f} {balances.filingStatus:2d}")

from finparams import modelParams,personParams
model = Model(modelParams)
model.people = [Person(personParams[0]),Person(personParams[1])]
balances = Balances(model)
print("Year Incm Exps  Txbl  Roth  Ptax  Fed   CA  RMD PtxW Cnvt Hlth  Rtrn FS")
while model.alive():
    balances.update()
    printYear(model.year,model.people,balances)
    model.newYear()
