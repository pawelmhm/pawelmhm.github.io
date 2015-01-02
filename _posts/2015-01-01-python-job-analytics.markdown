---
layout: post
title:  "Analyzing job market for Python with pandas"
date:   2015-01-01 14:34:42
categories: python pandas
---

In this post I'm doing some simple data analytics of job market for python
programmes. I will be using [Python Pandas](http://pandas.pydata.org/)

My dataset comes from [reed.co.uk](http://www.reed.co.uk/jobs?keywords=python) - UK
job board. I created Scrapy script that crawls reed.co.uk 
python job section, and parses all ads it finds.  While
crawling I set high download delay of 2 seconds, low number of max
concurrent requests per domain and added descriptive user agent header 
linking back to my blog. If you are interested in source code for spider let me know.

I've chosen this specific job board because in contrast with other sites of this 
type it displays interesting information about each post.
Aside from boring marketing speech describing how exciting each 
position is, reed shows more interesting facts about each position such as
salary range and number of applications. I was curious if one can find some patterns
in all this, also analyzing this data is good way to learn/demonstrate
some Python Pandas functions. 

My data is stored in .csv file that has 615 records, all job ads found when searching
for Python, you can [download it here](https://docs.google.com/uc?id=0B6myg3n6dqcVblo5MzBzZjQ3TEk&export=download)

Let's feed our data to Pandas.

{% highlight python %}

In [1]: import pandas as pd
In [2]: data = pd.read_csv('reed.csv')
In [3]: data.columns
Out[3]: Index([u'salary_min', u'description', u'title', u'salary_max', u'applications', u'page_number', u'location', u'published', u'link', u'found', u'id'], dtype='object')

{% endhighlight %}

Since my data comes from Internet it made sense to do some normalization
at the level of extraction. What you get in .csv is not exactly raw data, it is 
partly processed. For example dates on reed are displayed either as 
specific date in 'day month' format (e.g. '24 December'), or as string 'just now' or 'yesterday', so 
I had to use some regular expressions to extract proper data and then format all 
as ISO date string. Similarly with salary data it could be either posted as string 
'From 20 000 to 30 000' or just '20 000 per annum'.
I decided to use two fields: "salary_max" which is higher value of salary range, and
"salary_min" as lower value. If there was only one value posted I assumed value
present is salary_max.

### Location, location, location

First of all it makes sense to ask: where are Python positions located?

{% highlight python %}

In [37]: data.location.value_counts().head(10)
Out[37]: 
London         203
Cambridge       42
Reading         19
Bristol         19
Manchester      16
Devon           15
Berkhamsted     15
Oxford          11
Cardiff          8
USA              8
dtype: int64
{% endhighlight %}

If you know UK job market you're probably not suprised by domination of London. 
Almost 1/3 of all jobs are in London. Cambridge's second spot is interesting, 
as is high position of Bristol and Reading. 

Given high amount of open positions in each city, one wonders if market is 
perhaps saturated in London or Cambridge. 
How many applications per position do we have in top 10 locations?

Let's create smaller data set with job ads only from top 10 cities for
Python programmers:

{% highlight python %}

In [113]: toplocations = data.location.value_counts().head(10)
In [114]: mask = data.location.isin(toplocations.keys())
In [115]: tops = data[mask]

{% endhighlight %}

and now let's see how many applications are there per job post

{% highlight python %}

In [183]: applications = tops.groupby('location').applications.sum()
In [184]: ads = tops.groupby('location').id.count()
In [185]: applications / ads
Out[185]: 
location
Berkhamsted    2.333333
Bristol        4.157895
Cambridge      2.523810
Cardiff        3.250000
Devon          7.666667
London         7.935961
Manchester     2.125000
Oxford         4.181818
Reading        3.631579
USA            5.375000
dtype: float64

{% endhighlight %}

Seems like everyone wants to work in London and no one wants work in Manchester 
and Cambridge. Bristol attracts talent as does Oxford, but keep in mind low 
number of positions there. Devon has unusually high number of applications
per ad, which seems interesting.

Let's check if our calculations are correct (as you read my post please feel free
to check all my calculations, also let me know if there is some smarter, easier way
of getting some specific result).

{% highlight python %}
In [371]: cam = data[data.location=='Cambridge'].applications.sum() / float(data[data.location == 'Cambridge'].id.count())
In [372]: cam
Out[372]: 2.5238095238095237

{% endhighlight %}

### What determines number of applications

When browsing data you quickly notice uneven distribution of applications.
Some positions have zero applications, and some have relatively high number. For
example this query will give you number of applicantions for each Cambridge job.

{% highlight python %}
In [373]: data[data.location == 'Cambridge'][['location', 'applications']]

{% endhighlight %}

You can see lots of ads with zero applications and some unusually popular posts.
One position is particularly attractive, it attract 17 applicants. 

Why are there so many applications there? 

Is it the salary? 

{% highlight python %}

In [222]: data[data.applications == top_ad][data.location == 'Cambridge'][['applications', 'salary_max', 'salary_min']]
Out[222]: 
     applications  salary_max  salary_min
445            17         NaN        

{% endhighlight %}

No, salary is not given. Actually nothing in my data 
explains why this position is so popular so I had to follow link (I store all links to
job records in link columns, this is mostly for testing of accuracy of data
extraction), perhaps I missed something?

{% highlight python %}
In [238]: data[data.applications == top_ad][data.location == 'Cambridge'].link.values
Out[238]: array([ 'http://www.reed.co.uk/jobs/senior-graduate-software-engineers-web-developers-iot/25336524#/jobs?keywords=python&cached=True&pageno=18'], dtype=object)

{% endhighlight %}

If you follow [link](http://www.reed.co.uk/jobs/senior-graduate-software-engineers-web-developers-iot/25336524#/jobs?keywords=python&cached=True&pageno=18) and read description you'll see
that it's just entry level position, keywords "graduate" probably attract
people without experience with Python, so this would explain high application
rate.

This got me thinking: is there a strong link between a post being
entry level position and high number of applicants? We could do some
natural language processing to identify entry level positions, but 
this would probably require separate blog article, so for now, let's just
try checking if some keyword is present in description, for example
keyword 'graduate'.

{% highlight python %}

In [389]: filter = data.description.str.contains('graduate', case=False)
# mean of applications if there is keyword 'graduate' in description
In [390]: data[filter].applications.mean()
Out[390]: 12.0
# 'graduate' not present in description
In [391]: data[filter == False].applications.mean()
Out[391]: 4.3551236749116606
# mean salary if 'graduate' in description
In [392]: data[filter].salary_max.mean()
Out[392]: 27714.285714285714
# mean salary if 'graduate' not in description
In [393]: data[filter == False].salary_max.mean()
Out[393]: 62014.893506493507

{% endhighlight %}

Which in nutshell means: if you have some experience in Python 
you have on average 4 competitors to your position. Given that the most of the 
time recruiters are inviting 4-5 people to interview, you should probably get to interview 
if you worked with Python before.

### Salaries

To get data about salary grouped by location:

{% highlight python %}
In [244]: tops.groupby('location').salary_max.mean()
Out[244]: 
location
Berkhamsted    203714.285714
Bristol         52352.941176
Cambridge       46720.000000
Cardiff         36714.285714
Devon                    NaN
London          62846.376812
Manchester      74733.333333
Oxford          56666.666667
Reading         41642.857143
USA            154285.714286
Name: salary_max, dtype: float64

In [245]: tops.groupby('location').salary_min.mean()
Out[245]: 
location
Berkhamsted    177142.857143
Bristol         38294.117647
Cambridge       36400.000000
Cardiff         27285.714286
Devon                    NaN
London          47963.768116
Manchester      59866.666667
Oxford          46000.000000
Reading         32428.571429
USA            127857.142857
Name: salary_min, dtype: float64

{% endhighlight %}

Two things are strange here, unusually high values for Berkhamsted
and USA and absolutely no wage data for Devon. Are people really getting
that much in Berhamsted and USA?

As a side note, the fact that we have USA in our data set is because
of inconsitency in job postings on reed. For UK posts location is specified
as city, for US posts we get USA as location, without adding city. To get
actual US city where position is located we would have to parse description
which would be difficult to do, so I decided to keep it as it is without
normalizing this to city string.

Are these wages in Berkhamsted so high? I suspected either cheating here
or error in my script extracting data, so to actually check this I had to
follow those links and see raw data. 

Turns out it's [cheating on agency side](http://www.reed.co.uk/jobs/payroll-superstar/26069681#/jobs?keywords=python&cached=True&pageno=22).
Payroll superstar title hides rather small wages of 20k per annum. Since
agency that uses this trick is responsible for 10 job postings
out of all 15 Python jobs in Berkhamsted it is natural that it distorts
results. What's more this job is actually not work of Python 
programmer, but was caught in our results because of reed indexing
which caught reference to monty python. 

And for USA jobs? Are they really getting so much more then UK engineers?
Let's look at descriptions...

{% highlight python %}

In[260]: tops[tops.location=='USA'].description.values
Out[260]: 
array([ 'Software Developer - C & Linux/Unix - San Francisco - To c.$150,000 + bonus + relocation + bens. This role will involve designing and developing systems for the delivery of media content to consumers on a variety of devices, worldwide. This role offers a starting salary of up to $150,000 (possibly...',
       '  Senior Data Scientist / Manager   New York / New Jersey   $150,000 - $200,000 base salary + performance related annual bonus and exceptional benefits  Are you interested in working as a Senior Data Scientist / Manager for a hugely exciting, fast-paced, dynamic and globally renowned financial services...',
       'Software Developer - iOS, C/C++ and/or Java - San Francisco - To c.$130,000 + bonus + relocation + bens. This role will involve designing and developing SDKs and APIs that are used by iPhone, iPad and iOS developers around the world. This role offers a starting salary of up to $130,000 (possibly higher...',
       'Software Developer - C & Linux/Unix - San Francisco - To c.$150,000 + bonus + relocation + bens. This role will involve designing and developing systems for the delivery of media content to consumers on a variety of devices, worldwide. This role offers a starting salary of up to $150,000 (possibly...',
       'Software Developer - C & Linux/Unix - San Francisco - To c.$150,000 + bonus + relocation + bens. This role will involve designing and developing systems for the delivery of media content to consumers on a variety of devices, worldwide. This role offers a starting salary of up to $150,000 (possibly...',
       '  Data Scientist, Analytics   New York City, New York   $100,000 - $150,000 base salary + performance related annual bonus  Are you interested in working as a Data Scientist for a forward thinking, dynamic, innovative and customer focused online retailer where exceptional levels of career progression...',
       'Cloud Engineer - C/C++, Linux, AWS, Openstack - San Francisco - To c.$150,000 + bonus + relocation + bens. This role will involve designing and developing cloud software applications to improve the delivery of media content to consumers on a variety of devices, worldwide. This role offers a starting salary...',
       '  Algorithm Engineer New York City, New York $120,000 - $150,000 base salary + performance related annual bonus + benefits  The opportunity to work for the coolest, most innovative and cutting-edge digital media organization in New York City and arguably across the entire globe should not be passed upon...'], dtype=object)

{% endhighlight %}

All salaries are given in dollars not in pounds! Actual difference is not as
big as it seems. Yet even after adjusting to pound it seems that US salaries
are much higher at around 84-100k per annum. Whether actual take home wages
are higher in US is not completely evident. When comparing salaries between
two countries you have to ask yourself if you really compare apple to apples. 
Taxes, social security contributions and health care make a big difference to
actual take home pay and it is not clear if they are always specified in same way.
Perhaps they publish salaries without tax in US and with tax in UK, 
just like they publish prices of goods with tax in UK and without tax in US.

Finally aggregate data for UK as a whole:

{% highlight python %}

In [263]: data.salary_max.mean()
Out[263]: 59689.428571428572

In [264]: data.salary_min.mean()
Out[264]: 46540.220338983054

{% endhighlight %}

### Position without applicants

One interesting thing about job market for Python programmers is unusually
high number of positions for which there is no applications.
{% highlight python %}
In [88]: zeros = data[data.applications.eq(0)]
In [89]: zeros.id.count()
Out[89]: 101
{% endhighlight %}

One out of six jobs has zero applications. It has to be difficult to find
experienced python dev these days. 

But one can also ask why some positions don't get any interest.
First of all maybe they were just recently published and noone had the time 
to apply yet. Luckily I'm storing date published and date found in my data, 
so we can get number of days each add is on market from these fields. 
My script stores both dates as isoformat string. To get number of days
we need to convert isoformat date to timedelta and then to integer.

With pandas we can actually easily add new columns to DataFrame, so let's do this.
I will add new column "daysOn" - that contains timedelta between date published
and date found by my spider.

Adding new column is simple, just assign another series to DataFrame:

{% highlight python %}

In [291]: zeros["daysOn"] = zeros.found.astype(np.datetime64) - zeros.published.astype(np.datetime64)

In [292]: zeros[["found", "published", "daysOn"]].head(3)
Out[292]: 
                        found                   published  \
0  2014-12-26T21:54:34.050102  2014-12-22T21:54:34.049654   
2  2014-12-26T21:54:34.054577  2014-12-22T21:54:34.054197   
5  2014-12-26T21:54:34.063716  2014-12-26T21:54:34.063350   

                  daysOn  
0 4 days 00:00:00.000448  
2 4 days 00:00:00.000380  
5 0 days 00:00:00.000366  

{% endhighlight %}

At this point we have extra column "daysOn" which contains timedelta object
representing time that passed between date of publication and date when
each ad was found. Note that we're using [numpy datetime](http://docs.scipy.org/doc/numpy/reference/arrays.datetime.html) which exposes
slighly different api from python's native datetime.timedelta object
To actually get number of days we need to cast our timedelta to int
and representing number of days.o

{% highlight python %}

In [293]: zeros.daysOn = zeros.daysOn.apply(lambda a:np.timedelta64(a, 'D').astype(int))

In [294]: zeros[["found", "published", "daysOn"]].head(3)
Out[294]: 
                        found                   published  daysOn
0  2014-12-26T21:54:34.050102  2014-12-22T21:54:34.049654       4
2  2014-12-26T21:54:34.054577  2014-12-22T21:54:34.054197       4
5  2014-12-26T21:54:34.063716  2014-12-26T21:54:34.063350       0

{% endhighlight %}

Now let's eliminate those ads which are on job market only for zero days

{% highlight python %}

In [307]: zeros = zeros[zeros.daysOn.eq(0) == False]

In [309]: zeros[["found", "published", "daysOn"]].head(3)
Out[309]: 
                         found                   published  daysOn
0   2014-12-26T21:54:34.050102  2014-12-22T21:54:34.049654       4
2   2014-12-26T21:54:34.054577  2014-12-22T21:54:34.054197       4
12  2014-12-26T21:54:34.081788         2014-12-17T00:00:00       9

{% endhighlight %}

At this point 'zeros' frame contains only ads that are on market for more then 
one day, and no one had applied for them yet. 

Average time on market is two weeks.

{% highlight python %}
In [337]: zeros.daysOn.mean()
Out[337]: 14.329787234042554

{% endhighlight %}

Where are those positions located?

{% highlight python %}

In [311]: zeros.location.value_counts()
Out[311]: 
London             25
Cambridge          13
Manchester          6
Southampton         3
Surrey              3
Bristol             2
Cheltenham          2

{% endhighlight %}

Fun fact: salary for those position is actually higher from average.

{% highlight python %}

In [315]: zeros.salary_max.describe()
Out[315]: 
count        58.000000
mean      66736.793103
std       46585.508446
min       28000.000000
25%       40000.000000
50%       56300.000000
75%       75000.000000
max      276000.000000
Name: salary_max, dtype: float64

In [316]: data.salary_max.describe()
Out[316]: 
count       413.000000
mean      59689.428571
std       43279.344537
min       22000.000000
25%       36000.000000
50%       50000.000000
75%       65000.000000
max      276000.000000
Name: salary_max, dtype: float64

{% endhighlight %}

What types of jobs are these? Probably those that require lots 
of experience, we can tell that only two of them contain
word graduate. Juding by presence of some keywords like: 
"lead" or "experience" and salary above mean they are probably 
roles for experienced devs, and description seems scares people off.

{% highlight python %}
# probably not entry level positions, only two of 101 contain 'graduate'
In [351]: zeros[zeros.description.str.contains('graduate')].id.count()
Out[351]: 2
# which keywords are present? 'lead'...
In [358]: zeros[zeros.description.str.contains('lead', case=False)].id.count()
Out[358]: 42
# ... 'experience' 
In [359]: zeros[zeros.description.str.contains('experience', case=False)].id.count()
Out[359]: 40
{% endhighlight %}
