class FilingStatus:
    Single=0
    Married=1

class FedTax:
    # tax calculation requires brackets in decending order
    brackets = (
        (250.525,501.050),
        (197.300,394.600),
        (103.350,206.700),
        (48.475,96.950),
        (11.925,23.850),
        (0,0))
    rates = (0.35,0.32,0.24,0.22,0.12,0.10)
    deduction=(14.6,29.2)

class CaTax:
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
    deduction = (5.54,11.08)

class CapgainsTax:
    brackets=(
        (533.400,600.050),
        (48.351,96.701),
        (0,0))
    rates=(0.20,0.15,0.0)

class Person:
    def __init__(self,age,retireAge,deathAge,salary,pretaxFraction,rothFraction):
        self.age = age
        self.retireAge = retireAge
        self.deathAge = deathAge
        self.salary = salary
        self.pretaxFraction = pretaxFraction
        self.rothFraction = rothFraction
        
class Balances:
    def __init__(self,params,people):
        self.params = params
        self.taxable = params.taxableStart
        self.pretax = params.pretaxStart
        self.roth = params.rothStart
        self.people = people
        
    def update(self):
        if len(self.people)==1: self.filingStatus=FilingStatus.Single
        else: self.filingStatus=FilingStatus.Married

        income = self.calculateIncome()
        # how much are we contributing to roth/pretax
        roth,pretax = self.calculateRothAndPretax(income)
        capgains = self.taxable*self.params.marketReturn
        taxableIncome = income-pretax
        self.fedtax = self.calculateTax(taxableIncome,FedTax) \
            + self.calculateCapgainsTax(income,capgains)
        # california taxes capital gains as income
        self.catax = self.calculateTax(taxableIncome+capgains,CaTax)
        # update totals with our contributions
        tottax = self.fedtax+self.catax
        self.pretax += pretax
        self.roth += roth
        self.taxable += income-roth-pretax-tottax-self.params.expenses
        # market returns
        self.pretax*=(1+self.params.marketReturn)
        self.roth*=(1+self.params.marketReturn)
        self.taxable*=(1+self.params.marketReturn)

    def calculateRothAndPretax(self,income):
        roth=0
        pretax=0
        for p in self.people:
            roth+=income*p.rothFraction
            pretax+=income*p.pretaxFraction
        return roth,pretax

    def calculateIncome(self):
        income = 0
        for p in self.people: income+=p.salary
        return income

    def calculateTax(self,income,taxtype):
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

    def calculateCapgainsTax(self,income,capgains):
        for rate,brackets in zip(CapgainsTax.rates,CapgainsTax.brackets):
            if income>brackets[self.filingStatus]:
                return rate*capgains
        return 0
        
class People:
    def __init__(self,params):
        self.people=[]
        for i in range(2):
            self.people.append(Person(params.ages[i],params.retireAges[i],params.deathages[i],params.salaries[i],params.pretaxFractions[i],params.rothFractions[i]))
        self.year = params.startYear
    def newYear(self):
        self.year+=1
        remove = []
        for person in self.people:
            person.age+=1
        remaining = [p for p in self.people if p.age < p.deathAge]
        self.people = remaining
    def number(self):
        return len(self.people)
    def alive(self):
        return self.number()>0

def printYear(people,balances):
    print(f"{people.year} {balances.taxable:4.0f} {balances.roth:4.0f} {balances.pretax:4.0f} {balances.fedtax:4.0f} {balances.catax:4.0f}")

from finparams import Params
params = Params()
people = People(params)
balances = Balances(params,people.people)
print("Year Txbl Roth Ptax Fed  CA  ")
while people.alive():
    balances.update()
    printYear(people,balances)
    people.newYear()
