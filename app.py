import os

from datetime import datetime, timedelta, date
from pytrends.request import TrendReq

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import pandas as pd

import requests

from components import SEARCH_INPUT, STATISTIC_1, STATISTIC_2, STATISTIC_3

SHADOW = '5px 5px 5px lightgrey'

TEXT_NOTES = []   ### GLOBAL VARIABLE THAT HOLDS TEXT NOTES

test_card = '-' 

def pytrend_graph(keywords):

    maxstep = 269
    overlap = 40
    step = maxstep - overlap + 1

    kw_list = [keywords]
    start_date = datetime(2018, 11, 1).date()

    ## FIRST RUN ##

    # Login to Google. Only need to run this once, the rest of requests will use the same session.
    pytrend = TrendReq()

    # Run the first time (if we want to start from today, otherwise we need to ask for an end_date as well
    today = datetime.today().date()
    old_date = today
    #old_date = datetime(2019, 2, 26).date()

    pytrend = TrendReq()

    # Go back in time
    new_date = today - timedelta(days=step)

    # Create new timeframe for which we download data
    timeframe = new_date.strftime('%Y-%m-%d')+' '+old_date.strftime('%Y-%m-%d')
    pytrend.build_payload(kw_list=kw_list, timeframe=timeframe)
    interest_over_time_df = pytrend.interest_over_time()  ### KeyError occurs in several cases due to this line

    # RUN ITERATIONS
    while new_date > start_date:

        ### Save the new date from the previous iteration.
        # Overlap == 1 would mean that we start where we
        # stopped on the iteration before, which gives us
        # indeed overlap == 1.
        old_date = new_date + timedelta(days=overlap - 1)

        ### Update the new date to take a step into the past
        # Since the timeframe that we can apply for daily data
        # is limited, we use step = maxstep - overlap instead of
        # maxstep.
        new_date = new_date - timedelta(days=step)
        # If we went past our start_date, use it instead
        if new_date < start_date:
            new_date = start_date

        # New timeframe
        timeframe = new_date.strftime('%Y-%m-%d') + ' ' + old_date.strftime('%Y-%m-%d')
        print(timeframe)

        # Download data
        pytrend.build_payload(kw_list=kw_list, timeframe=timeframe)
        temp_df = pytrend.interest_over_time()
        if (temp_df.empty):
            raise ValueError(
                'Google sent back an empty dataframe. Possibly there were no searches at all during the this period! Set start_date to a later date.')
        # Renormalize the dataset and drop last line
        for kw in kw_list:
            beg = new_date
            end = old_date - timedelta(days=1)

            # Since we might encounter zeros, we loop over the
            # overlap until we find a non-zero element
            for t in range(1, overlap + 1):
                # print('t = ',t)
                # print(temp_df[kw].iloc[-t])
                if temp_df[kw].iloc[-t] != 0:
                    scaling = interest_over_time_df[kw].iloc[t - 1] / temp_df[kw].iloc[-t]
                    # print('Found non-zero overlap!')
                    break
                elif t == overlap:
                    print('Did not find non-zero overlap, set scaling to zero! Increase Overlap!')
                    scaling = 0
            # Apply scaling
            temp_df.loc[beg:end, kw] = temp_df.loc[beg:end, kw] * scaling
        interest_over_time_df = pd.concat([temp_df[:-overlap], interest_over_time_df])

    return(interest_over_time_df.reset_index())

def get_date(created):
    return datetime.fromtimestamp(created)

def letters(input):
    return ''.join([c for c in input if c.isalpha()])

def search_api(term):
    topics_dict = { "datePublished":[],
                "description":[],
                "name":[], "provider":[],
                "url": []}
    
    print('results for: '+ term)
    #print('status: '+r['status'])
    #if r['status'] == 'error':
    #    print(r)
    

    for page in [0,100, 200]:
        r = requests.get("https://microsoft-azure-bing-news-search-v1.p.rapidapi.com/"+
                                "search?count=100&offset="+str(page)+"&mkt=en-US&q="+term,
          headers={
            "X-RapidAPI-Key": "8ec5444edfmshaeb696c526371fap128461jsn402d28919eed"
          }
        ).json()
     
        for submission in r['value']:
            topics_dict["datePublished"].append(submission['datePublished'])
            topics_dict["description"].append(submission['description'])
            topics_dict["name"].append(submission['name'])
            topics_dict["provider"].append(submission['provider'][0]['name'])
            topics_dict["url"].append(submission['url'])
    print('totle news results: '+ str(r['totalEstimatedMatches'])) 
    df = pd.DataFrame(topics_dict)
    print('bing news results: '+ str(len(df['url'])))
    df['datePublished'] = pd.to_datetime(df['datePublished'])
    df['date'] = [d.date() for d in df['datePublished']]
    df['date'] = pd.to_datetime(df['date'])
    start_split_date = datetime(2018,11,1)
    #end_split_date = datetime(2019,1,31)
    df = df[(df["date"] > start_split_date)]
    df.drop_duplicates(inplace=True)
    print('bing news results: '+ str(len(df['url'])))
    return df

def search_reddit(search_term):
    topics_dict = { "title":[],
                    "score":[],
                    "id":[], "url":[],
                    "comms_num": [],
                    "created": [],
                    "body":[]}

    for submission in reddit.subreddit('News').search(search_term, sort='top', time_filter = 'year', limit=300):
        topics_dict["title"].append(submission.title)
        topics_dict["score"].append(submission.score)
        topics_dict["id"].append(submission.id)
        topics_dict["url"].append(submission.url)
        topics_dict["comms_num"].append(submission.num_comments)
        topics_dict["created"].append(submission.created)
        topics_dict["body"].append(submission.selftext)
    df = pd.DataFrame(topics_dict)
    _timestamp = df["created"].apply(get_date)
    df = df.assign(timestamp = _timestamp)
    df['date'] = [d.date() for d in df['timestamp']]
    df['date'] = pd.to_datetime(df['date'])
    start_split_date = datetime(2018,11,1)
    #end_split_date = datetime(2019,1,31)
    df = df[(df["date"] > start_split_date)]
    #df = df[(df['date'] < end_split_date)]
    return df

def contextweb(search):
    r = requests.get("https://contextualwebsearch-websearch-v1.p.rapidapi.com/api/Search/" 
                     "NewsSearchAPI?autoCorrect=true&pageNumber=1&pageSize=50&q=" + search +
                     "&safeSearch=false&fromPublishedDate=2018-10-18",
      headers={
        "X-RapidAPI-Key": "8ec5444edfmshaeb696c526371fap128461jsn402d28919eed"
      }
    ).json()
    return r

def dfmaker(r):
    articles = [[article['datePublished'], article['title'], article['description'], article['url'], article['keywords']]
                for article in r['value']]
    df_articles = pd.DataFrame(data = articles,
                               columns = ['date', 'title', 'description', 'url', 'keywords'])
    df_articles['date']=pd.to_datetime(df_articles['date'])
    df_articles['date'] = [day.date() for day in df_articles['date']]
    df_articles['date'] = df_articles['date'].astype("datetime64[ns]") 
    return df_articles

external_stylesheets = [         #### GET FONT-AWESOME CSS TO ADD ICONS  
    {
        'href': "https://use.fontawesome.com/releases/v5.6.1/css/all.css",
        'rel': 'stylesheet',
        'integrity': "sha384-gfdkjb5BdAXd+lj+gudLWI+BXq4IuLW5IT+brZEZsLFm++aCMlF1V92rMkPaX4PP",
        'crossorigin': 'anonymous'
    },
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.title = 'SmartTrends beta'

server = app.server

app.config['suppress_callback_exceptions']=True

bing_df = pd.read_csv('bing_news_headlines.csv', parse_dates=['date'])
reddit_df = pd.read_csv('reddit.csv', parse_dates=['date'])
us_trends = pd.read_csv('us_trends.csv', parse_dates = ['date'])
gstories = pd.read_csv('google_stories.csv', parse_dates = ['date'])


# layout
app.layout = html.Div([

            ### TOP BAR WITH SEARCH INPUT
            html.Div(
                className='tile is-parent',  ### OVERRIDE BULMA STYLING TO FIX THE HEADER ON TOP
                style={'backgroundColor': '#F0760A', 'position': 'fixed', 'width': '100%', 'top': 0, 'left': 0, 'zIndex': 5000},
                children=[
                html.Img(src="./assets/peppercom.png",              ### ADD NAVBAR LOGO IMAGE
                    style={"objectFit": "fill"}),  ### OVERRIDE BULMA STYLING
                html.Span(className="tile"), 
                html.H2("SmartTrends beta",  ### REMOVE html.Span to push Heading to left
                        className='subtitle is-4 has-text-white is-marginless'),  ### ADD SOME HEADING
                html.Span(className="tile"), SEARCH_INPUT]),
            html.Br(), html.Br(), html.Br(),   ### ADD SOME SPACE TO MAKE UP FOR FIXED NAVBAR ON TOP
            html.Nav(className="level",
                children=[          ### ADD NAVBAR FOR RESULTS KEYWORD 
                    html.P( className="subtitle is-6", style={"marginLeft": 100, "marginBottom": 0},
                            children="Results for: moon", id='results-for'), ## SHOW KEYWORD THROUGH CALLBACK
                ],  ### ADD STYLING TO RESULTS BAR
                style={'height': 50, 'backgroundColor': 'white', 'boxShadow': "0px 5px 5px lightgrey"}), 
            #html.Br(),
            html.Div(
                className="tile", 
                children=[      ### USE BULMA TILES TO ARRANGE ALL THE SECTIONS 
                    html.Div(className="tile is-9 is-vertical", children=[

                                                           html.Div(className="tile is-12 is-radiusless",children=[ 
                                                            html.Div(className="tile is-child is-4", children=[STATISTIC_1]),  ### CARD 1
                                                            html.Div(className="tile is-child is-4", children=[STATISTIC_2]),   ### CARD 2
                                                            html.Div(className="tile is-child is-4", children=[STATISTIC_3]),]), ### CARD 3
                                                            html.Div(  ### SET SOME STYLING TO DEAL WITH TILES HEIGHT & STUFF
                                                                className="tile is-12 notification has-background-white is-radiusless", 
                                                                children=[dcc.Graph(id='Graph', style={'width': '100%'})], ### ADD GRAPH
                                                                style={'margin': 10, 'boxShadow': SHADOW, 'width': '98%'}),  
                                                            html.Div(
                                                                className="tile is-12 notification has-background-white is-radiusless", 
                                                                children=[dcc.Graph(id='data-table', ### ADD DATA TABLE
                                                                    style={'width': '100%', 'margin': 0})], 
                                                                style={'margin': 10, 'boxShadow': SHADOW, 'width': '98%'})]),
                    html.Div(
                        className="tile is-vertical notification has-background-grey-light is-radiusless", 
                        children=[html.Div(className="has-text-white", style={'width': '100%'},
                            children=[    #### CREATE INSIGHTS COLUMN AS VERTICAL CHILD
                                html.P("Notes", className="has-text-weight-bold"),
                                #html.Br(),  ### ADD INPUT FILED
                                #dcc.Input(className="input is-rounded", type='text', id='notes-input', placeholder='NOTES'),
                                ### ADD INPUT BUTTON
                                #html.Button("Create Note", className="button is-rounded is-dark", 
                                #    id='notes-button', type='submit',
                                #    style={'width': '100%', 'backgroundColor': '#F0760A', 'color': 'white', 'border': 0}),
                                html.Hr(),   ### ADD SECTION TO DISPLAY CREATED NOTES
                                html.Div(id='show-notes', ### USE CALLBACK TO ADD CUSTOM NOTES
                                    children=[
                                    html.Div("- The tool does not currently support Boolean and doesnt require quotations around phrases"),
                                    html.Br(),
                                    html.Div("- The search is NOT case-sensitive"),
                                    html.Br(),
                                    html.Div("- Putting an * in the search (e.g. donut*) will show web search results in red - called context_web"),
                                    html.Br(),
                                    html.Div("- Data is available from October 20 - July 26"),
                                    html.Br(),
                                    html.Div("- From Feb 1 - 10 the tool briefly went offline")]
                                    ),
                                        ])],
                        style={'margin': 10, 'boxShadow': SHADOW, 'overflow': 'hidden', 'maxHeight': 2000}),
                    ], style={'marginLeft': 100, 'marginRight': 100}),
            ])



# callback for search bar
@app.callback(
    dash.dependencies.Output('Graph', 'figure'),
    [dash.dependencies.Input('search_button', 'n_clicks')],
    [dash.dependencies.State('Keywords', 'value')]
)
def update_figure(n_clicks, value):
    if value is not None:
        keyword = value
        print(value)
    else:
        keyword = 'moon'

    search_bing_df = bing_df[bing_df['headlines'].str.contains(letters(keyword), case=False)]
    count_bing_df = search_bing_df.set_index(['date','headlines']).count(level='date')

    search_reddit_df = reddit_df[reddit_df['title'].str.contains(letters(keyword), case=False)]
    count_reddit_df = search_reddit_df.set_index(['date','title']).count(level='date')

    search_gstories = gstories[gstories['keywords'].str.contains(letters(keyword), case=False)]
    count_gstories = search_gstories.set_index(['date', 'keywords']).count(level='date')

    generated_df = pytrend_graph(letters(keyword))
    if len(generated_df) == 0:      ## create dummy DF in case unwanted search returns empty dataframe
        generated_df = pd.DataFrame({'date': '2018-11-07', keyword: 0, 'isPartial': False}, index=[0])  
    #print(generated_df, generated_df.shape, generated_df.size, len(generated_df))

    #generated_df = search_reddit(keyword)

    search_us_trends_df = us_trends[us_trends['name'].str.contains(letters(keyword), case=False, )]
    count_us_trends_df = search_us_trends_df[['date', 'name']].groupby(['date', 'name']).agg('count').reset_index()
    count_us_trends_df = count_us_trends_df.groupby(['date']).nunique()

    if str('*') in str(keyword):
        #generated_news_df = search_api(letters(keyword))
        #count_news_df = generated_news_df.set_index(['date','name']).count(level='date')
        #normalize news_api scale
        #count_news_df['description'] = count_news_df['description'] * (float(generated_df[100:][generated_df.columns[1]].max()) / (count_news_df['description'].max()))

        generated_context = contextweb(letters(keyword))
        generated_context = dfmaker(generated_context)
        count_context_df = generated_context.set_index(['date', 'description']).count(level='date')
        count_context_df['title'] = count_context_df['title'] * (float(generated_df[100:][generated_df.columns[1]].max()) / (count_context_df['title'].max()))
        #print(count_context_df)
    else:
        #count_us_trends_df = pd.DataFrame({keyword: 0, 'isPartial': False, 'name': 0 }, index=['2019-02-20'])
        #count_news_df = pd.DataFrame({keyword: 0, 'isPartial': False, 'description': 0 }, index=['2019-02-20'])
        
        #search_news_df = news_df[news_df['title'].str.contains(keyword, case=False)]
        #count_news_df = news_df.set_index(['date','title']).count(level='date')
        #count_news_df['score'] = count_news_df['score'] *10

        count_context_df = pd.DataFrame({keyword: 0, 'isPartial': False, 'title': 0 }, index=['2019-02-20'])

    return{
            'data':[go.Bar(
                    x=count_bing_df.index,
                    y=count_bing_df['publications'],
                    name='Top News Headlines (count)',
                    yaxis='y2'#,
                    # mode='markers'
                ),
                go.Bar(
                    x=count_reddit_df.index,
                    y=count_reddit_df['domain'],
                    name='Top Reddit Mentions (count)',
                    yaxis='y2'#,
                    # mode='markers'
                ),
                go.Bar(
                   x=count_gstories.index,
                   y=count_gstories['publication'],
                   name='Google Stories (count)',
                   yaxis='y2'
                   #connectgaps=True
                ),
                go.Scatter(
                    x=count_context_df.index,
                    y=count_context_df['title'],
                    name = 'Context_web (scaled values)',
                    connectgaps=True
                ),
                go.Scatter(
                    x=generated_df['date'][60:],
                    y=generated_df[generated_df.columns[1]][60:],
                    name = 'Search Volume (scaled values)',
                    connectgaps=True
                ),
                go.Bar(
                    x=count_us_trends_df.index,
                    y=count_us_trends_df['name'],
                    name = 'Twitter Trends',
                    yaxis='y2'
                )
                ],
        'layout':go.Layout(
                    #legend=dict(x=0, y=-.6, orientation= 'h'),
                    legend={'orientation': 'h'},
                    #title='Results for: '+keyword,
                    barmode='stack',            ### ADD BARMODE as 'stack' to stack the bar graphs
                    clickmode='select+event',   ### ADD CLICKMODE to capture click event and click data point
                    yaxis=dict(
                        title='Overall Volume',
                        showgrid=False,
                        zeroline=False
                    ),
                    yaxis2=dict(
                        title='Top Hits',
                        showgrid=False,
                        zeroline=False,
                        titlefont=dict(
                            color='rgb(148, 103, 189)'
                        ),
                        tickfont=dict(
                            color='rgb(148, 103, 189)'
                        ),
                        overlaying='y',
                        side='right'
                    )
                )
    
    }

@app.callback(                           ###Callback to capture click event and update datatable 
    dash.dependencies.Output('data-table', 'figure'),
    [dash.dependencies.Input('Graph', 'clickData')],    ###clickData consist of X, curveNumber, and other values
    [dash.dependencies.State('Keywords', 'value')]
)
def update_table(click_value, keyword):
    curve_number = None
    print(click_value)
    if keyword is None:
        keyword = 'moon'
    if click_value is not None:                    ### Check the click_value to avoid errors 
        click_x = click_value['points'][0]['x']
        click_x = click_x.split(' ')[0]    ### Get the X value of click
        curve_number = click_value['points'][0]['curveNumber']  ### get the curve number, returns value between 0 and 3

    if curve_number == 0:          ###Curve 0 is Bing Bar Graph
        search_bing_df = bing_df[bing_df['headlines'].str.contains(keyword, case=False)]
        selected_df = search_bing_df[search_bing_df['date'] == click_x]
        #selected_df['link'] = '<a href = "' + selected_df['url'] + '">' + selected_df['headlines'] + '</a>'
        selected_df = selected_df[['date', 'headlines', 'publications']]

    elif curve_number == 1:        ### Curve 1 is Reddit Bar Graph 
        search_reddit_df = reddit_df[reddit_df['title'].str.contains(keyword, case=False)]
        selected_df = search_reddit_df[search_reddit_df['date'] == click_x]
        selected_df['title'] = selected_df['title'].str.slice(0,70)
        selected_df['link'] = '<a href = "' + selected_df['shortened'] + '">' + selected_df['title'] + '</a>'
        selected_df = selected_df[['date', 'link', 'subreddit']]
        print(selected_df)

    elif curve_number == 2:        ### Curve 2 is news_api line Graph 
        #generated_df = search_reddit(keyword)
        generated_df = gstories[gstories['keywords'].str.contains(letters(keyword), case=False)]
        selected_df = generated_df[generated_df['date'] == click_x]
        selected_df = selected_df[['date', 'headline', 'keywords']]
        #print (click_x)
        #print (curve_number)
        #print (keyword)
        #print (selected_df)
        #print (generated_df['date'])

    elif curve_number == 4:        ### Curve 4 is twitter Bar Graph 
        search_us_trends_df = us_trends[us_trends['name'].str.contains(keyword, case=False)]
        selected_df = search_us_trends_df[search_us_trends_df['date'] == click_x]
        selected_df['link'] = '<a href = "' + selected_df['url'] + '">' + selected_df['name'] + '</a>'
        selected_df = selected_df[['date', 'link', 'location']].drop_duplicates()
    
    else:                         ### ignore if curveNumber is 2 or 3 (line graphs) or click_value is None
        selected_df = pd.DataFrame({'Click Any Data Point on Bar Graphs to Populate the Table': '-'}, index=[0])

    TABLE_COLOR = '#F0760A'

    trace = go.Table(
        columnwidth = [40,300, 40],
        #header=dict(values=list(selected_df.columns),
        header=dict(values=list([i.upper() for i in selected_df.columns]),
                fill = dict(color=TABLE_COLOR), #'#C2D4FF'
                align = ['left', 'center', 'center'],
                font = {'color': 'white', 'size': 16, 'family': 'Arial'},
                line = {'color': 'white'}),
        cells=dict(values=[selected_df[i] for i in selected_df.columns],
               fill = dict(color='white'), #'#F5F8FF'
               align = ['left', 'center', 'center'],
               font = {'color': 'black', 'size': 15, 'family': 'Arial'}, 
               line = {'color': TABLE_COLOR}))

    data = [trace]
    layout = go.Layout(autosize=True, 
                        margin=go.layout.Margin(l=0, r=15, t=0, b=0, pad=4))  ### KEEP RIGHT MARGIN TO SHOW SCROLL BAR
    return {'data': data, 'layout': layout}

##### Callback to show RESULTS FOR on top: 
@app.callback(
    dash.dependencies.Output('results-for', 'children'),
    [dash.dependencies.Input('search_button', 'n_clicks')],
    [dash.dependencies.State('Keywords', 'value')]
)
def update_figure(n_clicks, value):
    if value == None:
        return "RESULTS FOR: " + 'moon'   ### THE DEFAULT KEYWORD IS moon
    return "Results for: " + str(value)  

##### Callbacks for the 3 cards on top

@app.callback(
    dash.dependencies.Output('card1', 'children'),
    [dash.dependencies.Input('search_button', 'n_clicks')],
    [dash.dependencies.State('Keywords', 'value')]
)
def update_card1(n_clicks, value):
    if value==None:
        return "-"
    return "-"

###
@app.callback(
    dash.dependencies.Output('card2', 'children'),
    [dash.dependencies.Input('search_button', 'n_clicks')],
    [dash.dependencies.State('Keywords', 'value')]
)
def update_card2(n_clicks, value):
    if value==None:
        return "-"
    return "-"

###
@app.callback(
    dash.dependencies.Output('card3', 'children'),
    [dash.dependencies.Input('search_button', 'n_clicks')],
    [dash.dependencies.State('Keywords', 'value')]
)
def update_card3(n_clicks, value):
    global test_card
    if value==None:
        return "-"
    return test_card

#### CALLBACK FOR NOTES

@app.callback(
    dash.dependencies.Output('show-notes', 'children'),
    [dash.dependencies.Input('notes-button', 'n_clicks')],
    [dash.dependencies.State('notes-input', 'value')]
)
def update_notes(n_clicks, value):
    global TEXT_NOTES      ### USE OF GLOBAL VARIABLE IS NOT RECOMMENDED BUT IS THE SIMPLEST WAY 
    if value== None:            ### GLOBAL VARIABLE IS NOT RELIABLE 
        return "YOU CAN INPUT YOUR CUSTOM NOTES HERE, THESE WILL GET DELETED UPON REFRESH"
    TEXT_NOTES.append(str(value))  ### APPEND TEXT NOTES IF NEW INPUT COMES IN
    
    if len(TEXT_NOTES) > 5:  ### SET MAXIMUM NOTES LIMIT TO 5
        TEXT_NOTES = TEXT_NOTES[1:]  ### REMOVE OLDEST NOTE IF MORE THAN 5 ITEMS

    child = []
    for i in TEXT_NOTES:   ### ADD HTML CONTENT TO CHILD TO BE DISPLAYED ON INSIGHTS COLUMN
        child.append(html.P(str(i), className="has-text-black"))
        child.append(html.Hr())
    
    return child 

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', debug=True)
