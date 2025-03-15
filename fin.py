Single=0
Married=1

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

class CapgainsTax:
    brackets=((533.400,48.351,0), # single
              (600.050,96.701,0)) # married
    rates=(0.20,0.15,0.0)

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
        
    def update(self):
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

        # only federal taxes socsec
        socsecTaxable = self.calcSocsecTaxable(self.income,self.socsecIncome)
        capgains = self.taxable*self.model.marketReturn
        taxableIncome = self.income-pretaxContrib
        fedTaxableIncome = taxableIncome+socsecTaxable-FedTax.deduction[self.filingStatus]

        # optional roth conversion
        convertBracket=self.model.rothConvertBracket
        self.convert=0
        if convertBracket>=0:
            self.convert=min(FedTax.brackets[self.filingStatus][convertBracket]-fedTaxableIncome,self.pretax) # max out this bracket
            if self.convert>0:
                fedTaxableIncome+=self.convert # pay taxes on conversion
                self.roth+=self.convert # add to roth
                self.pretax-=self.convert # remove from pretax
        self.fedtax = self.calcTax(fedTaxableIncome,FedTax) \
            + self.calcCapgainsTax(self.income,capgains)
        # california taxes capital gains as income
        stateTaxableIncome  = taxableIncome+capgains-StateTax.deduction[self.filingStatus]
        self.statetax = self.calcTax(stateTaxableIncome,StateTax)
        # update totals with our contributions
        tottax = self.fedtax+self.statetax

        self.pretax += pretaxContrib
        self.roth += rothContrib
        self.totExpenses = rothContrib+pretaxContrib+tottax+self.model.expenses
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

    def calcSocsecTaxable(self,income,socsecIncome):
        provisionalIncome = income + 0.5*socsecIncome # ignoring non-taxable interest
        if self.filingStatus==Single:
            if provisionalIncome<25: return 0
            elif provisionalIncome<34: return socsecIncome*0.5
            else: return socsecIncome*0.85
        if self.filingStatus==Married:
            if provisionalIncome<32: return 0
            elif provisionalIncome<44: return socsecIncome*0.5
            else: return socsecIncome*0.85
        
    def calcRothAndPretaxContrib(self,income):
        roth=0
        pretax=0
        for p in self.people:
            if p.age < p.retireAge:
                roth+=income*p.rothFraction
                pretax+=income*p.pretaxFraction
        return roth,pretax

    def calcRMD(self):
        # simplification: assume both spouses are same age so
        # we don't have to divide up pretax balances
        age = self.people[0].age
        if age>=75:
            yearsToLive = RMDTable[age-75][1]
            return self.pretax/yearsToLive
        else: return 0

    def calcIncome(self):
        income = 0
        socsecIncome = 0
        socsecPayrollTax = 0
        for p in self.people:
            if p.age < p.retireAge: income+=p.salary
            if p.age >= p.socsecAge: socsecIncome+=p.socsecIncome
            socsecSalary = min(p.salary,176.1)
            income -= 0.062*socsecSalary # remove socsec payroll taxes
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

    def calcCapgainsTax(self,income,capgains):
        for rate,bracket in zip(CapgainsTax.rates,CapgainsTax.brackets[self.filingStatus]):
            if income>bracket:
                return rate*capgains
        return 0
        
def printYear(year,people,balances):
    print(f"{year} {balances.income:4.0f} {balances.taxable:5.0f} {balances.roth:5.0f} {balances.pretax:5.0f} {balances.fedtax:4.0f} {balances.statetax:4.0f} {balances.rmd:4.0f} {balances.pretaxWithdrawn:4.0f} {balances.convert:4.0f} {balances.filingStatus:2d}")

from finparams import modelParams,personParams
model = Model(modelParams)
model.people = [Person(personParams[0]),Person(personParams[1])]
balances = Balances(model)
print("Year Incm  Txbl  Roth  Ptax  Fed   CA  RMD PtxW Cnvt FS")
while model.alive():
    balances.update()
    printYear(model.year,model.people,balances)
    model.newYear()
