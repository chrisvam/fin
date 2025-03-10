import sys

class FilingStatus:
    Single=0
    Married=1

class RMD:
    values = ((75,24.6), (76,23.7), (77,22.9), (78,22.0), (79,21.1), (80,20.2),
              (81,19.4), (82,18.5), (83,17.7), (84,16.8), (85,16.0), (86,15.2),
              (87,14.4), (88,13.7), (89,12.9), (90,12.2), (91,11.5), (92,10.8),
              (93,10.1), (94,9.5), (95,8.9), (96,8.4), (99,6.8,), (100,6.4),
              (101,6.0), (102,5.6), (103,5.2), (104,4.9), (105,4.6), (106,4.3),
              (107,4.1), (108,3.9), (109,3.7), (110,3.5), (111,3.4), (112,3.3),
              (113,3.1), (114,3.0), (115,2.9), (116,2.8), (117,2.7), (118,2.5),
              (119,2.3), (120,2.0))

class FedTax:
    # tax calculation requires brackets/rates in descending order
    brackets = (
        (250.525,501.050),
        (197.300,394.600),
        (103.350,206.700),
        (48.475,96.950),
        (11.925,23.850),
        (0,0))
    rates = (0.35,0.32,0.24,0.22,0.12,0.10)
    deduction=(14.6,29.2) # single/married

class StateTax: # for california
    # tax calculation requires brackets/rates in descending order
    brackets = (
        (721.315, 1442.629),
        (432.788, 865.575),
        (360.660, 721.319),
        (70.607, 141.213),
        (55.867, 111.733),
        (40.246, 80.491),
        (25.500, 50.999),
        (10.757, 21.513),
        (0,0))
    rates = (0.123,0.113,0.103,0.093,0.08,0.06,0.04,0.02,0.01)
    deduction = (5.54,11.08) # single/married

class CapgainsTax:
    brackets=(
        (533.400,600.050),
        (48.351,96.701),
        (0,0))
    rates=(0.20,0.15,0.0)

class Balances:
    def __init__(self,params):
        self.params = params
        self.taxable = params.taxableStart
        self.pretax = params.pretaxStart
        self.roth = params.rothStart
        self.people = params.people
        
    def update(self):
        if len(self.people)==1: self.filingStatus=FilingStatus.Single
        else: self.filingStatus=FilingStatus.Married

        self.income,self.socsecIncome = self.calcIncome()
        self.income+=self.socsecIncome

        # how much are we contributing to roth/pretax
        roth,pretax = self.calcRothAndPretax(self.income)

        # only federal taxes socsec
        socsecTaxable = self.calcSocsecTaxable(self.income,self.socsecIncome)
        capgains = self.taxable*self.params.marketReturn
        taxableIncome = self.income-pretax
        self.fedtax = self.calcTax(taxableIncome+socsecTaxable,FedTax) \
            + self.calcCapgainsTax(self.income,capgains)
        # california taxes capital gains as income
        self.statetax = self.calcTax(taxableIncome+capgains,StateTax)
        # update totals with our contributions
        tottax = self.fedtax+self.statetax

        self.pretax += pretax
        self.roth += roth
        self.totExpenses = roth+pretax+tottax+self.params.expenses
        netcash = self.income - self.totExpenses
        if netcash > 0:
            self.taxable += self.income-self.totExpenses
        else:
            # take from taxable first
            if self.taxable+netcash>0: self.taxable+=netcash
            else: # try pretax next
                # FIXME: NEED TO ADD PRETAX WITHDRAWALS TO TAXABLE INCOME
                # FIXME: NEED TO ADD RMDS
                self.taxable=0
                netcash+=self.taxable
                if self.pretax+netcash>0: self.pretax+=netcash
                else: # try roth
                    self.pretax=0
                    if self.roth+netcash>0: self.roth+=netcash
                    else: print('*** bankrupt ***',sys.exit(-1))
                    
        # market returns
        self.pretax*=(1+self.params.marketReturn)
        self.roth*=(1+self.params.marketReturn)
        self.taxable*=(1+self.params.marketReturn)

    def calcSocsecTaxable(self,income,socsecIncome):
        if self.filingStatus==FilingStatus.Single:
            if income<25: return 0
            elif income<34: return socsecIncome*0.5
            else: return socsecIncome*0.85
        if self.filingStatus==FilingStatus.Married:
            if income<32: return 0
            elif income<44: return socsecIncome*0.5
            else: return socsecIncome*0.85
        
    def calcRothAndPretax(self,income):
        roth=0
        pretax=0
        for p in self.people:
            if p.age < p.retireAge:
                roth+=income*p.rothFraction
                pretax+=income*p.pretaxFraction
        return roth,pretax

    def calcIncome(self):
        income = 0
        socsecIncome = 0
        for p in self.people:
            if p.age < p.retireAge: income+=p.salary
            if p.age >= p.socsecAge: income+=p.socsecIncome
        return income,socsecIncome

    def calcTax(self,income,taxtype):
        taxableIncome = income-taxtype.deduction[self.filingStatus]
        tax=0
        # depends on the tax bracket table being in descending order
        for rate,bracket in zip(taxtype.rates,taxtype.brackets):
            brkt = bracket[self.filingStatus]
            if taxableIncome>=brkt:
                amountInBracket = taxableIncome-brkt
                tax += rate*amountInBracket
                taxableIncome -= amountInBracket
                #print('***',income,rate,brkt,amountInBracket,taxableIncome,filingStatus)
        return tax

    def calcCapgainsTax(self,income,capgains):
        for rate,brackets in zip(CapgainsTax.rates,CapgainsTax.brackets):
            if income>brackets[self.filingStatus]:
                return rate*capgains
        return 0
        
class People:
    def __init__(self,params):
        self.people=params.people
    def newYear(self):
        removeIndices = []
        for i,p in enumerate(self.people):
            p.age+=1
            if p.age==p.deathAge: removeIndices.append(i)
        for i in removeIndices: del self.people[i]
    def number(self):
        return len(self.people)
    def alive(self):
        return self.number()>0

def printYear(year,people,balances):
    print(f"{year} {balances.income:4.0f} {balances.taxable:5.0f} {balances.roth:5.0f} {balances.pretax:5.0f} {balances.fedtax:4.0f} {balances.statetax:4.0f} {balances.filingStatus:2d}")

from finparams import Params
params = Params()
people = People(params)
balances = Balances(params)
print("Year Incm  Txbl  Roth  Ptax  Fed   CA FS")
while people.alive():
    balances.update()
    printYear(params.startYear,people,balances)
    params.startYear+=1
    people.newYear()
