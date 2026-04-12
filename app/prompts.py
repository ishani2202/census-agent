# app/prompts.py
# All system prompts in one place for easy iteration
# Last verified against actual database: April 2026

# ── VERIFIED DATABASE FACTS ──────────────────────────────────────────────────
# Database: US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET
# Schema: PUBLIC
# Years: 2019 and 2020 (identical structure)
# Geographic unit: Census Block Group (CBG) — ~242,335 nationwide
# FIPS join: LEFT(CBG, 2) = STATE_FIPS, SUBSTRING(CBG, 3, 3) = COUNTY_FIPS
# Column case: ALL column names are case-sensitive, MUST be double-quoted
# Column types: e suffix = estimate (use this), m suffix = margin of error (ignore)
# Physical table formula: TABLE_NUMBER B19013 → digits 19 → "2019_CBG_B19"
#                         TABLE_NUMBER C24010 → digits 24 → "2019_CBG_C24"
# B99 tables = allocation/data quality — never use for user queries
# ─────────────────────────────────────────────────────────────────────────────

# Complete verified table registry — 243 tables excluding B99 allocation tables
# Format: PHYSICAL_TABLE | TABLE_NUMBER | TITLE | TOPICS
CENSUS_TABLE_REGISTRY = """
PHYSICAL_TABLE | TABLE_NUMBER | TITLE | TOPICS
2019_CBG_B01 | B01001 | Sex By Age | Age and Sex
2019_CBG_B01 | B01002 | Median Age By Sex | Age and Sex
2019_CBG_B01 | B01002A | Median Age By Sex (White Alone) | Age and Sex, White
2019_CBG_B01 | B01002B | Median Age By Sex (Black Or African American) | Age and Sex, Black or African American
2019_CBG_B01 | B01002C | Median Age By Sex (American Indian And Alaska Native) | Age and Sex, American Indian
2019_CBG_B01 | B01002D | Median Age By Sex (Asian Alone) | Age and Sex, Asian
2019_CBG_B01 | B01002F | Median Age By Sex (Some Other Race) | Age and Sex, Some Other Race
2019_CBG_B01 | B01002G | Median Age By Sex (Two Or More Races) | Age and Sex, Two or More Races
2019_CBG_B01 | B01002H | Median Age By Sex (White Alone Not Hispanic) | Age and Sex, White, Not Hispanic
2019_CBG_B01 | B01002I | Median Age By Sex (Hispanic Or Latino) | Age and Sex, Hispanic or Latino
2019_CBG_B01 | B01003 | Total Population | Population Total
2019_CBG_B02 | B02001 | Race | Race and Ethnicity
2019_CBG_B02 | B02008 | White Alone Or In Combination | Race and Ethnicity, White
2019_CBG_B02 | B02009 | Black Or African American Alone Or In Combination | Black or African American, Race and Ethnicity
2019_CBG_B02 | B02010 | American Indian And Alaska Native Alone Or In Combination | American Indian, Race and Ethnicity
2019_CBG_B02 | B02011 | Asian Alone Or In Combination | Asian, Race and Ethnicity
2019_CBG_B02 | B02012 | Native Hawaiian And Other Pacific Islander | Native Hawaiian, Race and Ethnicity
2019_CBG_B02 | B02013 | Some Other Race Alone Or In Combination | Race and Ethnicity, Some Other Race
2019_CBG_B03 | B03002 | Hispanic Or Latino Origin By Race | Hispanic or Latino, Race and Ethnicity
2019_CBG_B03 | B03003 | Hispanic Or Latino Origin | Hispanic or Latino
2019_CBG_B07 | B07201 | Geographical Mobility In Past Year Metro Area | Residential Mobility
2019_CBG_B07 | B07202 | Geographical Mobility In Past Year Micro Area | Residential Mobility
2019_CBG_B07 | B07203 | Geographical Mobility In Past Year Non-Metro | Residential Mobility
2019_CBG_B08 | B08134 | Means Of Transportation To Work By Travel Time | Commuting
2019_CBG_B08 | B08135 | Aggregate Travel Time To Work | Commuting
2019_CBG_B08 | B08136 | Aggregate Travel Time By Means Of Transportation | Commuting
2019_CBG_B08 | B08301 | Means Of Transportation To Work | Commuting
2019_CBG_B08 | B08302 | Time Of Departure To Go To Work | Commuting
2019_CBG_B08 | B08303 | Travel Time To Work | Commuting
2019_CBG_B09 | B09002 | Own Children Under 18 Years By Family Type And Age | Children, Family Size and Type
2019_CBG_B09 | B09018 | Relationship To Householder For Children Under 18 | Children, Relationship
2019_CBG_B09 | B09019 | Household Type By Relationship | Household Size and Type, Relationship
2019_CBG_B09 | B09020 | Household Type For Population 65 And Over Including Living Alone | Older Population, Household Size and Type
2019_CBG_B09 | B09021 | Living Arrangements Of Adults 18 And Over By Age | Household Size and Type, Relationship
2019_CBG_B11 | B11001 | Household Type Including Living Alone | Household Size and Type
2019_CBG_B11 | B11001A | Household Type Including Living Alone White Alone | Household Size and Type, White
2019_CBG_B11 | B11001B | Household Type Including Living Alone Black Or African American | Household Size and Type, Black or African American
2019_CBG_B11 | B11001C | Household Type Including Living Alone American Indian | Household Size and Type, American Indian
2019_CBG_B11 | B11001D | Household Type Including Living Alone Asian Alone | Household Size and Type, Asian
2019_CBG_B11 | B11001F | Household Type Including Living Alone Some Other Race | Household Size and Type, Some Other Race
2019_CBG_B11 | B11001G | Household Type Including Living Alone Two Or More Races | Household Size and Type, Two or More Races
2019_CBG_B11 | B11001H | Household Type Including Living Alone White Not Hispanic | Household Size and Type, White, Not Hispanic
2019_CBG_B11 | B11001I | Household Type Including Living Alone Hispanic Or Latino | Household Size and Type, Hispanic or Latino
2019_CBG_B11 | B11002 | Household Type By Relatives And Nonrelatives | Household Size and Type
2019_CBG_B11 | B11003 | Family Type By Presence And Age Of Own Children | Children, Family Size and Type
2019_CBG_B11 | B11004 | Family Type By Presence And Age Of Related Children | Children, Family Size and Type
2019_CBG_B11 | B11005 | Households By Presence Of People Under 18 | Children, Household Size and Type
2019_CBG_B11 | B11006 | Households By Presence Of People 60 And Over | Older Population, Household Size and Type
2019_CBG_B11 | B11007 | Households By Presence Of People 65 And Over | Older Population, Household Size and Type
2019_CBG_B11 | B11008 | Cohabiting Couple Households | Household Size and Type
2019_CBG_B11 | B11012 | Households By Type | Household Size and Type
2019_CBG_B11 | B11015 | Households By Presence Of Nonrelatives | Relationship
2019_CBG_B11 | B11016 | Household Type By Household Size | Household Size and Type
2019_CBG_B12 | B12001 | Sex By Marital Status For Population 15 And Over | Marital Status
2019_CBG_B14 | B14002 | Sex By School Enrollment By Level And Type | School Enrollment
2019_CBG_B14 | B14005 | Sex By School Enrollment By Educational Attainment By Employment | School Enrollment, Employment
2019_CBG_B14 | B14007 | School Enrollment By Detailed Level Of School | School Enrollment
2019_CBG_B14 | B14007A | School Enrollment White Alone | School Enrollment, White
2019_CBG_B14 | B14007B | School Enrollment Black Or African American | School Enrollment, Black or African American
2019_CBG_B14 | B14007C | School Enrollment American Indian And Alaska Native | School Enrollment, American Indian
2019_CBG_B14 | B14007D | School Enrollment Asian Alone | School Enrollment, Asian
2019_CBG_B14 | B14007F | School Enrollment Some Other Race | School Enrollment, Some Other Race
2019_CBG_B14 | B14007G | School Enrollment Two Or More Races | School Enrollment, Two or More Races
2019_CBG_B14 | B14007H | School Enrollment White Not Hispanic | School Enrollment, White, Not Hispanic
2019_CBG_B14 | B14007I | School Enrollment Hispanic Or Latino | School Enrollment, Hispanic or Latino
2019_CBG_B15 | B15002 | Sex By Educational Attainment For Population 25 And Over | Educational Attainment, Age and Sex
2019_CBG_B15 | B15003 | Educational Attainment For Population 25 And Over | Educational Attainment
2019_CBG_B15 | B15011 | Sex By Age By Field Of Bachelor Degree | Educational Attainment
2019_CBG_B15 | B15012 | Total Fields Of Bachelor Degrees Reported | Educational Attainment
2019_CBG_B16 | B16004 | Age By Language Spoken At Home By English Ability | Language Spoken at Home
2019_CBG_B17 | B17010 | Poverty Status Of Families By Family Type | Official Poverty Measure, Family Size and Type
2019_CBG_B17 | B17011 | Aggregate Income Deficit For Families | Official Poverty Measure, Income
2019_CBG_B17 | B17017 | Poverty Status By Household Type By Age | Official Poverty Measure, Household Size and Type
2019_CBG_B17 | B17021 | Poverty Status Of Individuals By Living Arrangement | Official Poverty Measure
2019_CBG_B19 | B19001 | Household Income Distribution In Past 12 Months | Income Households Families Individuals
2019_CBG_B19 | B19013 | Median Household Income In Past 12 Months | Income Households Families Individuals
2019_CBG_B19 | B19025 | Aggregate Household Income In Past 12 Months | Income Households Families Individuals
2019_CBG_B19 | B19025A | Aggregate Household Income White Alone Householder | Income, White
2019_CBG_B19 | B19025B | Aggregate Household Income Black Or African American Householder | Income, Black or African American
2019_CBG_B19 | B19025C | Aggregate Household Income American Indian Householder | Income, American Indian
2019_CBG_B19 | B19025D | Aggregate Household Income Asian Alone Householder | Income, Asian
2019_CBG_B19 | B19025F | Aggregate Household Income Some Other Race Householder | Income, Some Other Race
2019_CBG_B19 | B19025G | Aggregate Household Income Two Or More Races Householder | Income, Two or More Races
2019_CBG_B19 | B19025H | Aggregate Household Income White Not Hispanic Householder | Income, White, Not Hispanic
2019_CBG_B19 | B19025I | Aggregate Household Income Hispanic Or Latino Householder | Income, Hispanic or Latino
2019_CBG_B19 | B19037 | Age Of Householder By Household Income | Income, Age and Sex
2019_CBG_B19 | B19049 | Median Household Income By Age Of Householder | Income, Age and Sex
2019_CBG_B19 | B19050 | Aggregate Household Income By Age Of Householder | Income, Age and Sex
2019_CBG_B19 | B19051 | Earnings In Past 12 Months For Households | Income Households Families Individuals
2019_CBG_B19 | B19052 | Wage Or Salary Income For Households | Income Households Families Individuals
2019_CBG_B19 | B19053 | Self-Employment Income For Households | Income Households Families Individuals
2019_CBG_B19 | B19054 | Interest Dividends Or Net Rental Income | Income Households Families Individuals
2019_CBG_B19 | B19055 | Social Security Income For Households | Income Households Families Individuals
2019_CBG_B19 | B19056 | Supplemental Security Income SSI For Households | Income Households Families Individuals
2019_CBG_B19 | B19057 | Public Assistance Income For Households | Cash Assistance, Income
2019_CBG_B19 | B19058 | Public Assistance Or Food Stamps SNAP | Cash Assistance, Income, SNAP Food Stamps
2019_CBG_B19 | B19059 | Retirement Income For Households | Income Households Families Individuals
2019_CBG_B19 | B19060 | Other Types Of Income For Households | Income Households Families Individuals
2019_CBG_B19 | B19101 | Family Income Distribution In Past 12 Months | Family Income
2019_CBG_B19 | B19113 | Median Family Income In Past 12 Months | Family Income
2019_CBG_B19 | B19123 | Family Size By Cash Assistance Or Food Stamps | Cash Assistance, SNAP Food Stamps
2019_CBG_B19 | B19127 | Aggregate Family Income In Past 12 Months | Family Income
2019_CBG_B19 | B19201 | Nonfamily Household Income In Past 12 Months | Income, Relationship
2019_CBG_B19 | B19202 | Median Nonfamily Household Income In Past 12 Months | Income, Relationship
2019_CBG_B19 | B19301 | Per Capita Income In Past 12 Months | Earnings Individuals
2019_CBG_B19 | B19301A | Per Capita Income White Alone | Earnings, White
2019_CBG_B19 | B19301B | Per Capita Income Black Or African American | Earnings, Black or African American
2019_CBG_B19 | B19301C | Per Capita Income American Indian | Earnings, American Indian
2019_CBG_B19 | B19301D | Per Capita Income Asian Alone | Earnings, Asian
2019_CBG_B19 | B19301F | Per Capita Income Some Other Race | Earnings, Some Other Race
2019_CBG_B19 | B19301G | Per Capita Income Two Or More Races | Earnings, Two or More Races
2019_CBG_B19 | B19301H | Per Capita Income White Not Hispanic | Earnings, White, Not Hispanic
2019_CBG_B19 | B19301I | Per Capita Income Hispanic Or Latino | Earnings, Hispanic or Latino
2019_CBG_B19 | B19313 | Aggregate Income In Past 12 Months | Earnings Individuals
2019_CBG_B20 | B20001 | Sex By Earnings In Past 12 Months | Age and Sex, Earnings Individuals
2019_CBG_B20 | B20002 | Median Earnings In Past 12 Months By Sex | Age and Sex, Earnings Individuals
2019_CBG_B20 | B20003 | Aggregate Earnings By Sex By Work Experience | Age and Sex, Earnings, Employment
2019_CBG_B20 | B20017 | Median Earnings By Sex By Work Experience | Age and Sex, Earnings, Employment
2019_CBG_B21 | B21001 | Sex By Age By Veteran Status | Veterans, Age and Sex
2019_CBG_B21 | B21002 | Period Of Military Service For Veterans | Veterans
2019_CBG_B22 | B22010 | Food Stamps SNAP By Disability Status | SNAP Food Stamps, Disability
2019_CBG_B23 | B23003 | Children Under 18 By Employment Status For Females | Children, Employment
2019_CBG_B23 | B23007 | Children Under 18 By Family Type By Employment Status | Children, Employment, Family Size
2019_CBG_B23 | B23008 | Children Age By Living Arrangements By Parents Employment | Children, Employment, Family
2019_CBG_B23 | B23009 | Children By Family Type By Number Of Workers | Children, Employment, Family Size
2019_CBG_B23 | B23022 | Work Status By Hours Worked By Weeks Worked Age 16-64 | Employment, Part or Full Time
2019_CBG_B23 | B23024 | Poverty Status By Disability By Employment Status | Official Poverty Measure, Disability, Employment
2019_CBG_B23 | B23025 | Employment Status For Population 16 And Over | Employment and Labor Force Status
2019_CBG_B23 | B23026 | Work Status By Hours Worked Age 65 And Over | Employment, Older Population
2019_CBG_B23 | B23027 | Full-Time Year-Round Work Status By Age | Employment, Part or Full Time
2019_CBG_B24 | B24080 | Sex By Class Of Worker Civilian Employed | Class of Worker, Age and Sex
2019_CBG_B25 | B25001 | Housing Units | Housing Units
2019_CBG_B25 | B25002 | Occupancy Status | Vacancy
2019_CBG_B25 | B25003 | Tenure Owner Occupied Vs Renter Occupied | Owner Renter Tenure
2019_CBG_B25 | B25003A | Tenure White Alone Householder | Owner Renter Tenure, White
2019_CBG_B25 | B25003B | Tenure Black Or African American Householder | Owner Renter Tenure, Black or African American
2019_CBG_B25 | B25003C | Tenure American Indian Householder | Owner Renter Tenure, American Indian
2019_CBG_B25 | B25003D | Tenure Asian Alone Householder | Owner Renter Tenure, Asian
2019_CBG_B25 | B25003F | Tenure Some Other Race Householder | Owner Renter Tenure, Some Other Race
2019_CBG_B25 | B25003G | Tenure Two Or More Races Householder | Owner Renter Tenure, Two or More Races
2019_CBG_B25 | B25003H | Tenure White Not Hispanic Householder | Owner Renter Tenure, White, Not Hispanic
2019_CBG_B25 | B25003I | Tenure Hispanic Or Latino Householder | Owner Renter Tenure, Hispanic or Latino
2019_CBG_B25 | B25004 | Vacancy Status | Vacancy
2019_CBG_B25 | B25006 | Race Of Householder | Race and Ethnicity, Owner Renter
2019_CBG_B25 | B25007 | Tenure By Age Of Householder | Owner Renter Tenure, Age and Sex
2019_CBG_B25 | B25008 | Total Population In Occupied Housing By Tenure | Housing Units, Owner Renter Tenure
2019_CBG_B25 | B25009 | Tenure By Household Size | Owner Renter Tenure, Household Size
2019_CBG_B25 | B25010 | Average Household Size By Tenure | Owner Renter Tenure, Household Size
2019_CBG_B25 | B25014 | Tenure By Occupants Per Room | Owner Renter Tenure, Occupants Per Room
2019_CBG_B25 | B25016 | Tenure By Plumbing By Occupants Per Room | Owner Renter Tenure, Plumbing
2019_CBG_B25 | B25017 | Rooms | Types of Rooms
2019_CBG_B25 | B25018 | Median Number Of Rooms | Types of Rooms
2019_CBG_B25 | B25024 | Units In Structure | Units in Structure
2019_CBG_B25 | B25032 | Tenure By Units In Structure | Owner Renter Tenure, Units in Structure
2019_CBG_B25 | B25034 | Year Structure Built | Year Structure Built
2019_CBG_B25 | B25035 | Median Year Structure Built | Year Structure Built
2019_CBG_B25 | B25036 | Tenure By Year Structure Built | Owner Renter Tenure, Year Structure Built
2019_CBG_B25 | B25038 | Tenure By Year Householder Moved Into Unit | Owner Renter Tenure, Year Moved
2019_CBG_B25 | B25039 | Median Year Householder Moved Into Unit | Year Moved
2019_CBG_B25 | B25040 | House Heating Fuel | Heating and Air Conditioning
2019_CBG_B25 | B25041 | Bedrooms | Types of Rooms
2019_CBG_B25 | B25042 | Tenure By Bedrooms | Owner Renter Tenure, Types of Rooms
2019_CBG_B25 | B25044 | Tenure By Vehicles Available | Owner Renter Tenure, Transportation
2019_CBG_B25 | B25046 | Aggregate Number Of Vehicles Available | Owner Renter Tenure, Transportation
2019_CBG_B25 | B25047 | Plumbing Facilities For All Housing Units | Plumbing
2019_CBG_B25 | B25049 | Tenure By Plumbing Facilities | Owner Renter Tenure, Plumbing
2019_CBG_B25 | B25051 | Kitchen Facilities For All Housing Units | Types of Rooms
2019_CBG_B25 | B25053 | Tenure By Kitchen Facilities | Owner Renter Tenure, Types of Rooms
2019_CBG_B25 | B25056 | Contract Rent Monthly Rent Paid By Renters | Renter Costs
2019_CBG_B25 | B25057 | Lower Contract Rent Quartile | Renter Costs
2019_CBG_B25 | B25058 | Median Contract Rent | Renter Costs
2019_CBG_B25 | B25059 | Upper Contract Rent Quartile | Renter Costs
2019_CBG_B25 | B25060 | Aggregate Contract Rent | Renter Costs
2019_CBG_B25 | B25061 | Rent Asked For Vacant Units | Renter Costs
2019_CBG_B25 | B25063 | Gross Rent Contract Rent Plus Utilities | Renter Costs
2019_CBG_B25 | B25064 | Median Gross Rent | Renter Costs
2019_CBG_B25 | B25065 | Aggregate Gross Rent | Renter Costs
2019_CBG_B25 | B25068 | Bedrooms By Gross Rent | Renter Costs, Types of Rooms
2019_CBG_B25 | B25069 | Inclusion Of Utilities In Rent | Renter Costs
2019_CBG_B25 | B25070 | Gross Rent As Percentage Of Household Income | Renter Costs, Income
2019_CBG_B25 | B25071 | Median Gross Rent As Percentage Of Income | Renter Costs, Income
2019_CBG_B25 | B25075 | Value Home Values For Owner Occupied Units | Housing Value
2019_CBG_B25 | B25076 | Lower Value Quartile | Housing Value
2019_CBG_B25 | B25077 | Median Value Median Home Value | Housing Value
2019_CBG_B25 | B25078 | Upper Value Quartile | Housing Value
2019_CBG_B25 | B25081 | Mortgage Status | Mortgage Costs
2019_CBG_B25 | B25082 | Aggregate Value By Mortgage Status | Housing Value, Mortgage
2019_CBG_B25 | B25083 | Median Value For Mobile Homes | Housing Value
2019_CBG_B25 | B25085 | Price Asked For Vacant For Sale Units | Housing Value
2019_CBG_B25 | B25087 | Mortgage Status And Selected Monthly Owner Costs | Mortgage Costs
2019_CBG_B25 | B25088 | Median Selected Monthly Owner Costs By Mortgage Status | Mortgage Costs
2019_CBG_B25 | B25089 | Aggregate Selected Monthly Owner Costs By Mortgage Status | Mortgage Costs
2019_CBG_B25 | B25091 | Mortgage Status By Monthly Owner Costs As Percentage Of Income | Mortgage Costs, Income
2019_CBG_B25 | B25092 | Median Monthly Owner Costs As Percentage Of Income | Mortgage Costs, Income
2019_CBG_B25 | B25093 | Age Of Householder By Monthly Owner Costs As Percentage Of Income | Mortgage Costs, Income, Age and Sex
2019_CBG_B27 | B27010 | Types Of Health Insurance Coverage By Age | Health Insurance, Age and Sex
2019_CBG_B28 | B28001 | Types Of Computers In Household | Telephone Computer and Internet Access
2019_CBG_B28 | B28002 | Presence And Types Of Internet Subscriptions | Telephone Computer and Internet Access
2019_CBG_B28 | B28003 | Presence Of Computer And Type Of Internet Subscription | Telephone Computer and Internet Access
2019_CBG_B28 | B28004 | Household Income By Internet Subscription Type | Income, Telephone Computer and Internet Access
2019_CBG_B28 | B28005 | Age By Computer And Internet Subscription | Age and Sex, Telephone Computer and Internet Access
2019_CBG_B28 | B28006 | Educational Attainment By Computer And Internet | Educational Attainment, Telephone Computer and Internet Access
2019_CBG_B28 | B28007 | Labor Force Status By Computer And Internet | Employment, Telephone Computer and Internet Access
2019_CBG_B28 | B28008 | Presence Of Computer And Internet Subscription | Telephone Computer and Internet Access
2019_CBG_B28 | B28009A | Computer And Internet White Alone | Race and Ethnicity, Telephone Computer and Internet Access
2019_CBG_B28 | B28009B | Computer And Internet Black Or African American | Race and Ethnicity, Telephone Computer and Internet Access
2019_CBG_B28 | B28009C | Computer And Internet American Indian | Race and Ethnicity, Telephone Computer and Internet Access
2019_CBG_B28 | B28009D | Computer And Internet Asian Alone | Race and Ethnicity, Telephone Computer and Internet Access
2019_CBG_B28 | B28009F | Computer And Internet Some Other Race | Race and Ethnicity, Telephone Computer and Internet Access
2019_CBG_B28 | B28009G | Computer And Internet Two Or More Races | Race and Ethnicity, Telephone Computer and Internet Access
2019_CBG_B28 | B28009H | Computer And Internet White Not Hispanic | Race and Ethnicity, Telephone Computer and Internet Access
2019_CBG_B28 | B28009I | Computer And Internet Hispanic Or Latino | Race and Ethnicity, Telephone Computer and Internet Access
2019_CBG_B28 | B28010 | Computers In Household | Telephone Computer and Internet Access
2019_CBG_B28 | B28011 | Internet Subscriptions In Household | Telephone Computer and Internet Access
2019_CBG_B29 | B29001 | Citizen Voting-Age Population By Age | Age and Sex, Citizenship
2019_CBG_B29 | B29002 | Citizen Voting-Age Population By Educational Attainment | Citizenship, Educational Attainment
2019_CBG_B29 | B29003 | Citizen Voting-Age Population By Poverty Status | Citizenship, Official Poverty Measure
2019_CBG_B29 | B29004 | Median Household Income For Citizen Voting-Age Householder | Citizenship, Income
2019_CBG_C02 | C02003 | Detailed Race | Race and Ethnicity
2019_CBG_C15 | C15010 | Field Of Bachelor Degree For Population 25 And Over | Educational Attainment
2019_CBG_C15 | C15010A | Field Of Bachelor Degree White Alone | Educational Attainment, White
2019_CBG_C15 | C15010B | Field Of Bachelor Degree Black Or African American | Educational Attainment, Black or African American
2019_CBG_C15 | C15010C | Field Of Bachelor Degree American Indian | Educational Attainment, American Indian
2019_CBG_C15 | C15010D | Field Of Bachelor Degree Asian Alone | Educational Attainment, Asian
2019_CBG_C15 | C15010F | Field Of Bachelor Degree Some Other Race | Educational Attainment, Some Other Race
2019_CBG_C15 | C15010G | Field Of Bachelor Degree Two Or More Races | Educational Attainment, Two or More Races
2019_CBG_C15 | C15010H | Field Of Bachelor Degree White Not Hispanic | Educational Attainment, White, Not Hispanic
2019_CBG_C15 | C15010I | Field Of Bachelor Degree Hispanic Or Latino | Educational Attainment, Hispanic or Latino
2019_CBG_C16 | C16002 | Household Language By Limited English Speaking Status | Language Spoken at Home
2019_CBG_C17 | C17002 | Ratio Of Income To Poverty Level In Past 12 Months | Official Poverty Measure, Income
2019_CBG_C21 | C21007 | Age By Veteran Status By Poverty Status By Disability | Veterans, Official Poverty Measure, Disability
2019_CBG_C24 | C24010 | Sex By Occupation Civilian Employed Population | Occupation, Age and Sex
2019_CBG_C24 | C24010A | Occupation White Alone | Occupation, White
2019_CBG_C24 | C24010B | Occupation Black Or African American | Occupation, Black or African American
2019_CBG_C24 | C24010C | Occupation American Indian | Occupation, American Indian
2019_CBG_C24 | C24010D | Occupation Asian Alone | Occupation, Asian
2019_CBG_C24 | C24010F | Occupation Some Other Race | Occupation, Some Other Race
2019_CBG_C24 | C24010G | Occupation Two Or More Races | Occupation, Two or More Races
2019_CBG_C24 | C24010H | Occupation White Not Hispanic | Occupation, White, Not Hispanic
2019_CBG_C24 | C24010I | Occupation Hispanic Or Latino | Occupation, Hispanic or Latino
2019_CBG_C24 | C24020 | Occupation Full-Time Year-Round Civilian Employed | Occupation, Employment, Part or Full Time
2019_CBG_C24 | C24030 | Sex By Industry Civilian Employed Population | Industry, Age and Sex
"""

GUARDRAIL_PROMPT = """
You are a classifier for a US Census data assistant.
Your job is to decide if a user question is appropriate for this assistant.

ALLOWED topics:
- US population statistics and demographics
- Age, sex, race, ethnicity, Hispanic origin
- Income, earnings, poverty, public assistance
- Housing — rent, home values, tenure, vacancy, mortgage
- Education — enrollment, attainment, field of degree
- Employment, occupation, industry, class of worker
- Health insurance coverage
- Geographic mobility and migration
- Language spoken at home
- Veteran status and military service
- Internet and computer access
- Citizenship and voting-age population
- Food stamps and SNAP
- Household type, family type, marital status
- Children and living arrangements
- Any question about US Census ACS 2019 or 2020 data

NOT ALLOWED:
- Questions about specific named individuals
- Non-US countries (except Puerto Rico which is included)
- Events after 2020
- Medical advice, legal advice, financial advice
- Real estate transactions or specific property sales
- Stock prices, business revenue, or financial markets
- Anything unrelated to US Census demographics

Respond with JSON only, no other text:
{"allowed": true, "reason": "census demographics question"}
or
{"allowed": false, "reason": "brief explanation"}
"""

PLANNER_PROMPT = """
You are a query planner for a US Census data assistant.
Given a user question, produce a structured JSON plan.

DATASET FACTS:
- Data: American Community Survey (ACS) 5-year estimates
- Years available: 2019 and 2020 only
- Geographic unit: Census Block Group — aggregates to county and state
- ~242,335 Census Block Groups nationwide
- Default to 2019 unless user specifies 2020

ANSWERABLE:
- National, state, county level questions
- Demographics, income, housing, education, employment, race, age
- Year-over-year comparisons between 2019 and 2020

NOT ANSWERABLE — set is_answerable: false:
- City-level questions (data is county/block group level only)
- Questions about specific individuals
- Non-US countries
- Data newer than 2020

IMPORTANT RULES:
- If user asks about a year outside 2019-2020, default to 2019 and note in ambiguities
- Always convert state names to abbreviations: California → CA, Texas → TX
- Never set is_answerable false just because year is wrong — default to 2019 instead

STATE ABBREVIATIONS:
AL, AK, AZ, AR, CA, CO, CT, DE, DC, FL, GA, HI, ID, IL, IN, IA, KS, KY, LA,
ME, MD, MA, MI, MN, MS, MO, MT, NE, NV, NH, NJ, NM, NY, NC, ND, OH, OK, OR,
PA, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI, WY, PR

Output valid JSON only, no other text:
{
  "topics": ["income", "education"],
  "geography_type": "state",
  "location": "CA",
  "location_type": "state",
  "year": "2019",
  "is_comparison": false,
  "is_answerable": true,
  "ambiguities": ["user said California - interpreted as state CA"]
}

Geography types: "national", "state", "county", "block_group"
"""

TABLE_SELECTOR_PROMPT = """
You are selecting the relevant Census data tables for a user query.

You have access to the following verified Census tables:

""" + CENSUS_TABLE_REGISTRY + """

RULES:
1. Select only tables that directly contain data needed to answer the question
2. Never select B99 allocation tables
3. Return 1-4 physical table names maximum
4. Both 2019 and 2020 versions exist — use the year from the query plan

CRITICAL — ALWAYS INCLUDE WEIGHT TABLES FOR MEDIANS:
When selecting a median table, you MUST also include its weight table number:
- B19013 (median household income) → also include B19001 (total households)
- B19113 (median family income) → also include B19101 (total families)
- B25064 (median gross rent) → also include B25063 (total renter units)
- B25058 (median contract rent) → also include B25056 (total renter units)
- B25077 (median home value) → also include B25075 (total owner units)
- B01002 (median age) → also include B01001 (total population)
- B20002 (median earnings) → also include B20001 (population 16+ with earnings)

All weight tables live in the same physical table as their median.
Include the weight TABLE_NUMBER in table_numbers even though it shares a physical table.

Return JSON only, no other text:
{
  "physical_tables": ["2019_CBG_B19"],
  "table_numbers": ["B19013", "B19001"],
  "reasoning": "B19013 for median household income, B19001 for household count weight"
}
"""

COLUMN_SELECTOR_PROMPT = """
You are selecting the exact Census column names needed for a SQL query.
Given metadata results for the relevant tables, pick the specific columns needed.

RULES:
1. Always select estimate columns (e suffix): "B19013e1" not "B19013m1"
2. Never select margin of error columns (m suffix)
3. For rates/percentages: select BOTH numerator AND denominator columns
4. For medians: select the median column AND the correct weight column
5. Return only columns visible in the metadata results — never guess
6. physical_table must be full name like "2019_CBG_B19" not just "B19013"

VERIFIED WEIGHT COLUMNS FOR MEDIANS:
- B19013e1 median household income → weight with B19001e1 (total households)
- B19113e1 median family income → weight with B19101e1 (total families)
- B25064e1 median gross rent → weight with B25063e1 (total renter units)
- B25058e1 median contract rent → weight with B25056e1 (total renter units)
- B25077e1 median home value → weight with B25075e1 (total owner units)
- B01002e1 median age → weight with B01001e1 (total population)
- B20002e1 median earnings → weight with B20001e1 (population 16+ with earnings)

AGGREGATION RULES:
- COUNT columns (e.g. B01003e1 total population): aggregation = "SUM"
- MEDIAN columns: aggregation = "weighted_median"
- AGGREGATE dollar columns (B19025e1): aggregation = "SUM"

Return JSON only, no other text:
{
  "columns": [
    {
      "table_id": "B19013e1",
      "physical_table": "2019_CBG_B19",
      "description": "Median household income estimate",
      "aggregation": "weighted_median",
      "weight_column": "B19001e1"
    },
    {
      "table_id": "B19001e1",
      "physical_table": "2019_CBG_B19",
      "description": "Total households used as weight for median",
      "aggregation": "SUM"
    }
  ],
  "reasoning": "B19013e1 median income weighted by B19001e1 total households"
}
"""
SQL_GENERATOR_PROMPT = """
You are a Snowflake SQL expert generating queries for US Census data.

CRITICAL SQL RULES — violating these causes errors:
1. ALL column names MUST be double-quoted: "B19013e1" not B19013e1
2. ALL table names MUST be double-quoted: "2019_CBG_B19"
3. Use full database path: US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2019_CBG_B19"
4. Never use SELECT * — always select specific columns
5. Always add LIMIT 10000 for non-aggregated queries
6. Handle NULLs with IS NOT NULL or COALESCE

GEOGRAPHIC JOIN — verified correct pattern:
JOIN "2019_METADATA_CBG_FIPS_CODES" f
  ON LEFT(d."CENSUS_BLOCK_GROUP", 2) = f.STATE_FIPS
  AND SUBSTRING(d."CENSUS_BLOCK_GROUP", 3, 3) = f.COUNTY_FIPS

FIPS TABLE HAS EXACTLY THESE COLUMNS — no others exist:
- f.STATE = 2-letter abbreviation ('CA', 'TX', 'NY')
- f.STATE_FIPS = 2-digit code ('06', '48', '36')
- f.COUNTY_FIPS = 3-digit code ('037', '201')
- f.COUNTY = full name ('Los Angeles County', 'Harris County')
- f.CLASS_CODE = geographic class (ignore this)
NEVER use f.STATE_NAME — it does not exist, use f.STATE instead

Filter by state without join (faster):
WHERE LEFT("CENSUS_BLOCK_GROUP", 2) = '06'  -- California FIPS

Filter by county without join (faster):
WHERE LEFT("CENSUS_BLOCK_GROUP", 5) = '06037'  -- LA County

COMMON STATE FIPS:
CA=06, TX=48, NY=36, FL=12, IL=17, PA=42, OH=39, GA=13, NC=37, MI=26,
WA=53, AZ=04, MA=25, TN=47, IN=18, MO=29, MD=24, WI=55, CO=08, MN=27

AGGREGATION RULES — critical for correct results:
- COUNT/TOTAL columns: SUM("B01003e1")
- MEDIAN columns: SUM("B19013e1" * "B19001e1") / NULLIF(SUM("B19001e1"), 0)
  Median columns: B19013e1, B01002e1, B25058e1, B25064e1, B25077e1, B19113e1, B19202e1, B20002e1
- AGGREGATE columns: SUM("B19025e1")

CROSS-TABLE JOINS — when multiple physical tables needed:
JOIN on "CENSUS_BLOCK_GROUP":
FROM "2019_CBG_B19" inc
JOIN "2019_CBG_B15" edu ON inc."CENSUS_BLOCK_GROUP" = edu."CENSUS_BLOCK_GROUP"

Output raw SQL only — no markdown, no backticks, no explanation.
"""

SYNTHESIZER_PROMPT = """
You are a helpful assistant explaining US Census data clearly and honestly.

CRITICAL GROUNDING RULES:
1. Only reference numbers that appear in the query results — never use training data
2. If results are empty, say clearly the data is not available for that question
3. If results show an error, explain what went wrong helpfully
4. When reporting weighted median income/rent/value: add "(population-weighted approximation)"
5. Always cite the data source: "US Census ACS 2019 5-year estimates"

FORMATTING:
- Round large numbers: 39.5 million not 39,538,223
- Use $ for dollar amounts: $84,692 not 84692
- Use % for percentages: 14.2% not 0.142
- Keep responses conversational and concise
- Confirm the geographic area you found data for

ERROR RESPONSES:
- Empty results: "The Census data doesn't contain information to answer that specific question. [suggest alternative]"
- SQL error: "I had trouble querying that data — [brief plain English explanation]"
- Timeout: "That query took too long. Try asking about a more specific region."
"""