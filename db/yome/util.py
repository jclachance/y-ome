# -*- coding: utf-8 -*-

from yome.models import Gene, Knowledgebase, KnowledgebaseGene, KnowledgebaseFeature

from datetime import timedelta
import pandas as pd
import re
from bs4 import BeautifulSoup
from IPython.display import HTML

def create(session, query_class, commit=False, **kwargs):
    """Add a new row to the database and return.

    Arguments
    ---------

    session: The SQLAlchemy session.

    query_class: The class to query.

    commit: If True, then commit. Otherwise flush.

    """
    res = query_class(**kwargs)
    session.add(res)
    if commit:
        session.commit()
    else:
        session.flush()
    return res

def get_or_create(session, query_class, commit=False, **kwargs):
    """Query the query_class, filtering by the given keyword arguments. If no result
    is found, then add a new row to the database. Returns result of the query.

    Arguments
    ---------

    session: The SQLAlchemy session.

    query_class: The class to query.

    commit: If True, then commit. Otherwise flush.

    """
    res = session.query(query_class).filter_by(**kwargs).first()
    if res is not None:
        return res, True
    return create(session, query_class, commit=commit, **kwargs), False

def format_seconds(total_sec):
    """Format a time delta.

    """
    delt = timedelta(seconds=total_sec)
    days = delt.days
    hours, rem = divmod(delt.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if seconds == 0:
        return '<1 s'
    s = '%s s' % seconds
    if minutes:
        s = '%d m ' % minutes + s
    if hours:
        s = '%d h ' % hours + s
    if days:
        s = '%d d ' % days + s
    return s

def to_df(query, cols=None):
    """Convert a SQLAlchemy query result to a DataFrame."""
    # Try to get column names
    if cols is None:
        cols = [x['name'] for x in query.column_descriptions]
    data = [{k: v for k, v in zip(cols, x)} for x in query]
    if len(data) == 0:
        return pd.DataFrame()
    return pd.DataFrame(data).loc[:, cols]

def apply_keyword(df, keyword, field, is_high):
    """Apply a keyword to the dataframe, and warn if it already has an
    annotation_quality. Give mismatches a 'tbd' label.

    """
    add, other = ('high', 'low') if is_high else ('low', 'high')
    df.loc[
        df[field].str.contains(keyword, flags=re.IGNORECASE) & (df.annotation_quality != other),
        'annotation_quality'
    ] = add
    # give mismatches a tbd label
    mismatch = df.loc[
        df[field].str.contains(keyword, flags=re.IGNORECASE) & (df.annotation_quality == other),
        'annotation_quality'
    ] = 'tbd'
    # if len(mismatch > 0):
    #     print(f'Mismatches for keyword {keyword} in {", ".join(mismatch.locus_tag.values)}')

# Based on https://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
def html_to_text(text):
    soup = BeautifulSoup(text, 'lxml')
    return soup.get_text()


def report(session, locus_tag):
    """Print a report of all features for a gene"""
    report = to_df(
        session.query(Gene.locus_id,
                      KnowledgebaseGene.primary_name,
                      KnowledgebaseGene.annotation_quality,
                      Knowledgebase.name.label('knowledgebase_name'),
                      KnowledgebaseFeature.feature_type,
                      KnowledgebaseFeature.feature)
        .join(KnowledgebaseGene)
        .join(Knowledgebase)
        .join(KnowledgebaseFeature)
        .filter(Gene.locus_id == locus_tag)
    )

    print(report.iloc[0, 0:2])

    report.knowledgebase_name = report.apply(lambda row: f"{row['knowledgebase_name']} ({row['annotation_quality']})", axis=1)
    report = report.drop(['locus_id', 'primary_name', 'annotation_quality'], axis=1)
    report = report.set_index(['knowledgebase_name', 'feature_type'])
    s = report.style.set_properties(**{'text-align': 'left'})
    return HTML(s.render())
