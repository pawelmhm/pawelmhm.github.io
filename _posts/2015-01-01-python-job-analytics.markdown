---
layout: post
title:  "Analyzing job market for Python with pandas"
date:   2015-01-01 14:34:42
categories: python pandas
---

In this post I'm doing some simple data analytics of python job
data using Python Pandas. 

My (rather small) dataset comes from reed.co.uk - which is UK
job posting. I wrote simple scrapy script that crawls reed.co.uk 
python job section, and parses all ads it finds. I've chosen this
specific job board because in contrast with other sites of this 
type it displays interesting information about each post. 

Aside from usual rather uninteresting marketing blah blah of job description
it shows interesting information about each position - salary range,
number of applications, and also date posted. 

I was curious if one can find some patterns
in all this and thought it's a good way to learn some Python Pandas functions. 

Our data can be downloaded [here](http://sport.pl), let's feed it to Panda.

{% highlight python %}

In [1]: import pandas as pd
In [2]: data = pd.read_csv('reed.csv')
In [3]: data.columns
Out[3]: Index([u'salary_min', u'description', u'title', u'salary_max', u'applications', u'page_number', u'location', u'published', u'link', u'found', u'id'], dtype='object')

{% endhighlight %}

Since my data comes from internet it made sense to do some slight normalizations
at the level of extraction. For example dates on reed are displayed either as 
specific date in format 24 December, or as string 'just now' or 'tomorrow', so 
if we want to get proper dates I had to use some regular expressions to extract
proper data and then format all as ISO date string. Similarly with salary data
it could be either posted as string 'From 20000 to 30000' or just '20000', 
usually it's per year, but sometimes there was string 'per week'. I decided
to use two fields: "salary_max" which is higher value of salary range, and
"salary_min" as lower value. If there was only one value posted I assumed this
is higher value. 

Ok so let's move to some analytics. First of all it makes sense to ask: where 
those Python jobs are?


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
Almost 1/3 of all jobs are in London. Cambridge second spot is interesting, 
as is high position of Bristol and Reading. 

Out of curiosity let's check what is the situation on job market in those
10 cities, how many applications per position do we have in top 10 locations?

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

Seems like everyone wants to work in London and no one wants work in Cambridge, 
Reading. Bristol looks like more attractive place to live but nothing beats 
attractiveness of London. Devon has unusually high number of applications
per ad, which seems interesting.

Let's check if our calculations are correct (I'm no data science expert, worth
double checking all my calculations).

{% highlight python %}

In [196]: data[data.location == 'Cambridge'][['location', 'applications']]

{% endhighlight %}

You can see lots of ads with zero applications and some unusually popular posts.
Why are some ads attracting 17 applicants while other attract zero? We will
try to explain this later. Perhaps higher salary is involved? Let's check most 
popular job ad for Cambridge.

{% highlight python %}

In [222]: data[data.applications == top_ad][data.location == 'Cambridge'][['applications', 'salary_max', 'salary_min']]
Out[222]: 
     applications  salary_max  salary_min
445            17         NaN        

{% endhighlight %}
No it's not the salary, salary is not disclosed, and most of the time in reed
if it's not shown it means there it's not high. Why is it so attractive? 
Nothing in my data explains it so I had to follow link (I store all links to
job records in link columns, this is mostly for testing of accuracy of data
extraction)

{% highlight python %}
In [238]: data[data.applications == top_ad][data.location == 'Cambridge'].link.values
Out[238]: array([ 'http://www.reed.co.uk/jobs/senior-graduate-software-engineers-web-developers-iot/25336524#/jobs?keywords=python&cached=True&pageno=18'], dtype=object)

{% endhighlight %}

If you follow [link](http://www.reed.co.uk/jobs/senior-graduate-software-engineers-web-developers-iot/25336524#/jobs?keywords=python&cached=True&pageno=18) and read description you'll see
that it's just entry level position, keywords "graduate" probably attract
people without experience with Python, so this would explain high application
rate.

### Salaries

To get data about salary:


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

Two things are strange here, unusually high values for Berkhamstead
and USA and absolutely no wage data for Devon. Are people really getting
that much in Berhamstead and USA?

As a side note, the fact that we have USA in our data set is because
of inconsitency in job postings on reed. For UK posts location is specified
as city, for US posts we get USA as location, without adding city. To get
actual US city where position is located we would have to parse description
which would be difficult to do, so I decided to keep it as it is without
normalizing this to city string.

So are these wages in Berkhamsted so high? I suspected either cheating here
or error in my script extracting data, so to actually check this I had to
follow those links and see raw data. 

Turns out it's [cheating on agency side](http://www.reed.co.uk/jobs/payroll-superstar/26069681#/jobs?keywords=python&cached=True&pageno=22).
Payroll superstar title hides rather small wages of 20k per annum. Since
agency that uses this trick is responsible for 10 job postings
out of all 15 Python jobs in Berkhamsted it is natural that it distorts
results. What's more this job is actually not work of Python 
programmer, but was caught in our results because of reed indexing
which caught reference to monty Python. 

And for USA jobs? Are they really getting so much more then UK engineers?
This can be clarified if we actually look at descriptions of those jobs
we quickly realize that higher values are because of 

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

All salaries are given in dollars not in pounds, so actual difference is not 
that big. But still even after adjusting to pound it seems that US salaries
are much higher at around 84-100k per annum. Whether actual take home wages
are higher in US is not completely evident. When comparing salaries between
two countries you have to ask if you really compare apple to apples. Do they
really include all taxes, social security contributions and health care
payments in those US salaries? Perhaps they publish salaries without tax in US
and with tax in UK, just like they publish prices of goods (in US they often
give you price without tax, in UK you always have total price). 

Looking at salary data you can see that Manchester is actually quite attractive.
Only around 2 applications per position and wages that are on average higher from
those in London, where there is considerable crowd of 7 applicatns per position.

Finally aggregate data for UK as a whole:

{% highlight python %}

In [263]: data.salary_max.mean()
Out[263]: 59689.428571428572

In [264]: data.salary_min.mean()
Out[264]: 46540.220338983054

{% endhighlight %}

Open questions:

is there always a correlation between entry level position and number of 
applicants, as in case of this most popular Cambridge ad? 

{% highlight python %}

In [277]: data[data.description.str.contains('graduate', case=False)].applications.mean()
Out[277]: 12.0

In [278]: data[data.description.str.contains('graduate', case=False) == False].applications.mean()
Out[278]: 4.3551236749116606

In [279]: data[data.description.str.contains('graduate', case=False) == False].salary_max.mean()
Out[279]: 62014.893506493507

In [280]: data[data.description.str.contains('graduate', case=False)].salary_max.mean()
Out[280]: 27714.285714285714

{% endhighlight %}

Which in nutshell means: if you have more then one year of experience in Python 
you have on average 4 competitors to your position. Given that the way agencies
work (inviting 4-5 people per interview), you should get to interview stage in
UK.
