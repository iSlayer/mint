#!/usr/bin/env python
import mintapi
import pandas as pd
import sys
import numpy as np

# TODO:
#   Select average timeframe

all_income_categories = []
all_expense_categories = []
all_ignore_categories = []


def unstacked_summary(df):
    """A function to unstack the year and month of a grouped dataframe"""
    return df.unstack(['Year', 'Month']).fillna(0)


def stacked_summary(df):
    """A function to stack the year and month of a dataframe"""
    return df.stack(['Year', 'Month']).fillna(0)


def create_category_hiearchy(cats, categoryType):
    """A function that creates a dict of the root and subroot categories"""
    dict_out = {}

    for key in cats.keys():
        name = cats[key]['name']
        parent_name = cats[key]['parent']['name']
        cat_type = cats[key]['categoryType']

        if cat_type == categoryType:
            # Check if parent name is Root and should be the key
            if parent_name == 'Root':
                # Check to see if key exists
                if name not in dict_out.keys():
                    # If not, add key to dict and empty list
                    dict_out[name] = []
            else:
                if parent_name == 'Root':
                    continue

                # Check if parent_name already key
                if parent_name not in dict_out.keys():
                    # If not, add the key and empty list
                    dict_out[parent_name] = []

                # Add the subcategory
                dict_out[parent_name].append(name)

    return dict_out


def populate_list_category(dict_in):
    """A function that creates a list of the root and subroot categories"""
    list_out = []
    for key, value in dict_in.items():
        list_out.append(key)
        list_out.extend(value)

    return [x.lower() for x in list_out]


def dataframe_from_mint(username, password):
    """A function that signs into mint.com and queries transaction info"""
    # Connect to mint api and login with credentials
    mint = mintapi.Mint(username, password)

    # Load all possible categories
    cats = mint.get_categories()

    # Load the transactions
    df = mint.get_transactions()

    # Load Net Worth
    net_worth = mint.get_net_worth()

    # Specific columns
    columns = ['date', 'description', 'amount', 'transaction_type',
            'category', 'account_name']
    df = df[columns]
    df['root_cat'] = np.nan
    df['sub_cat'] = np.nan

    # Name the rows by date
    df = df.set_index('date')

    return df, cats, net_worth


def convert_transaction_types(df):
    """A function that converts transactions into income, expesnse, & ignore"""
    global all_income_categories
    global all_expense_categories
    global all_ignore_categories

    # Make postive numbers income and negative numbers expenses
    idx_debit = df['transaction_type'].str.match('debit')
    df.loc[idx_debit, 'amount'] *= -1

    # Better transaction_type names
    # Hand-modified
    df.loc[df['category'].isin(all_income_categories), 'transaction_type'] = 'income'
    df.loc[df['category'].isin(all_expense_categories), 'transaction_type'] = 'expense'
    df.loc[df['category'].isin(all_ignore_categories), 'transaction_type'] = 'ignore'

    # Heuristic (credit is income, debit is expense)
    df.loc[df['transaction_type'] == 'credit', 'transaction_type'] = 'income'
    df.loc[df['transaction_type'] == 'debit', 'transaction_type'] = 'expense'

    return df


def populate_hiearchy(df, dict_hiearchy):
    """A function that fills the root & subroot categories in the dataframe"""
    for root, cat_list in dict_hiearchy.items():
        idx = df['category'].str.match(root.lower())

        df.loc[idx, 'root_cat'] = root
        df.loc[idx, 'sub_cat'] = root

        for cat in cat_list:
            idx = df['category'].str.match(cat.lower())

            df.loc[idx, 'root_cat'] = root
            df.loc[idx, 'sub_cat'] = cat

    return df


def group_dataframe(df):
    """A function that groups the dataframe by Year, Month, Transaction Type,
    Root Category, Subroot Category, and takes the sum of the Amounts"""
    # Category -> Year -> Month -> Transaction Type -> Root Cat -> Sub Cat
    return df.groupby([
        (df.index.year.rename('Year')),
        (df.index.month.rename('Month')),
        'transaction_type', 'root_cat', 'sub_cat']).sum()


def include_totals_in_dataframe(df):
    # Easier to manipulate data by unstacking years & months
    df = unstacked_summary(df)

    categories = df.index.tolist()

    # TODO: Sort categories: sort(income), sort(expense), ...
    # TODO: Is this needed, since I can groupby different levels
    # row_names = categories + [
    #     ('', '', 'Income Total'),
    #     ('', '', 'Expense Total'),
    #     ('', '', 'Ignore Total'),
    #     ('', '', 'Net Total'),
    # ]
    row_names = categories
    df_reindex = df.reindex(row_names, fill_value=0)

    # income_idx= [x[0] == 'income' for x in df_.index.tolist()]
    # expense_idx = [x[0] == 'expense' for x in df_reindex.index.tolist()]
    # ignore_idx = [x[0] == 'ignore' for x in df_reindex.index.tolist()]

    # df_reindex.loc[('', '', 'Income Total')] = df_reindex[income_idx].sum()
    # df_reindex.loc[('', '', 'Expense Total')] = df_reindex[expense_idx].sum()
    # df_reindex.loc[('', '', 'Ignore Total')] = df_reindex[ignore_idx].sum()
    # df_reindex.loc[('', '', 'Net Total')] = df_reindex.loc[[
    #     ('', '', 'Income Total'),
    #     ('', '', 'Expense Total')]].sum()

    return df_reindex


def total_sub_cat(df):
    """A function that calculates the totals by year and subroot categories."""
    df = unstacked_summary(df)
    return df.groupby(level=[0, 2]).sum()


def total_root_cat(df):
    """A function that calculates the totals by transaction and root categories."""
    df = unstacked_summary(df)
    return df.groupby(level=[0, 1]).sum()


def total_transaction_types(df):
    """A function that calculates the total by transaction type"""
    df = unstacked_summary(df)
    return df.groupby(level=0).sum()


def total_year_categories(df):
    """A function that calculates the total by year and root categories"""
    return df.groupby(level=[0, 3]).sum()


def total_root_by_year(df):
    """A function that calculates the total by year & root categories
    then unstacks the year"""
    return df.groupby(level=[0, 3]).sum().unstack(['Year']).fillna(0)


def average_last_12months(df, last_entry):
    """A function that averages the the previous 12 whole months"""
    df = df.groupby(level=[0, 1, 3]).sum().unstack(level=[0, 1]).fillna(0)

    # Check if data is on last day of the month
    # so that the current month can be averaged
    if last_entry.is_month_end:
        return df.iloc[:, -12:].mean(axis=1)
    else:
        return df.iloc[:, -12-1:-1].mean(axis=1)


def financial_independence(avg, net_worth, withdrawl_rate, return_rate):
    """A function that calculates financial independence and years to retirement"""
    global all_income_categories
    global all_expense_categories
    global all_ignore_categories

    withdrawl_rate = withdrawl_rate / 100
    return_rate = return_rate / 100

    # Proper indexing of income, expense, and ignore root_cats
    income_idx = avg.index.str.lower().isin(all_income_categories)
    expense_idx = avg.index.str.lower().isin(all_expense_categories)
    ignore_idx = avg.index.str.lower().isin(all_ignore_categories)

    df = pd.DataFrame()
    df = df.reindex(avg.index[expense_idx])
    df['Avg'] = avg.values[expense_idx]

    annual_income = avg[income_idx].sum() * 12
    annual_spending = avg[expense_idx].sum() * 12
    annual_ignore = avg[ignore_idx].sum() * 12

    annual_savings = annual_income + annual_spending
    annual_savings_rate = (annual_income + annual_spending) / annual_income

    # Expense breakdown
    df['Annual Expenses'] = avg[expense_idx] * 12
    df['Monthly Expenses'] = df['Annual Expenses'] / 12
    df['Daily Expenses'] = df['Annual Expenses'] / 365

    df['Percentage'] = df['Monthly Expenses'] / (annual_income / 12)
    df['Savings'] = df['Annual Expenses'] / withdrawl_rate

    fi_num = np.nper(return_rate / 12, -annual_savings / 12, -net_worth,
            -df['Savings'].sum(), 1) / 12

    df['FI'] = (df['Savings'] / df['Savings'].sum()) * fi_num

    tmp = df.sum()
    tmp.name = 'Total'
    df = df.append(tmp)

    return df


def main(argv):
    global all_income_categories
    global all_expense_categories
    global all_ignore_categories

    # Unpack arguments
    username = argv[0]
    password = argv[1]

    # Setup rates
    withdrawl_rate = 3.75
    return_rate = 5.00

    # Use mintapi to import data to dataframe
    df, cats, net_worth = dataframe_from_mint(username, password)
    last_entry = max(df.index)

    # Convert to hiearchy categories
    income_hiearchy = create_category_hiearchy(cats, 'INCOME')
    expense_hiearchy = create_category_hiearchy(cats, 'EXPENSE')
    ignore_hiearchy = create_category_hiearchy(cats, 'NO_CATEGORY')

    # Populate category groups
    all_income_categories = populate_list_category(income_hiearchy)
    all_expense_categories = populate_list_category(expense_hiearchy)
    all_ignore_categories = populate_list_category(ignore_hiearchy)

    # Add Parent_cat and sub_cat columns to transactions
    df = populate_hiearchy(df, income_hiearchy)
    df = populate_hiearchy(df, expense_hiearchy)
    df = populate_hiearchy(df, ignore_hiearchy)

    # Convert corresponsing transaction_types
    df = convert_transaction_types(df)

    # Group dataframe by:
    # 'Year', 'Month', 'transaction_type', 'root_cat', 'sub_cat'
    df_grouped = group_dataframe(df)

    # Calculate total sub_cat by Month & Year
    # df_total = include_totals_in_dataframe(df_grouped)
    df_cats_by_date = total_sub_cat(df_grouped)

    # Calculate total root_cat by Month & Year
    df_root_by_date = total_root_cat(df_grouped)

    # Calculate total Income, expense, & ignore by Month & Year
    # df_total = include_totals_in_dataframe(df_grouped)
    df_total_by_date = total_transaction_types(df_grouped)

    # Calculate total root_cat by Year
    df_root_by_year = total_root_by_year(df_grouped)

    # Average 12 month time frame
    average12 = average_last_12months(df_grouped, last_entry)

    # FI Stuff
    df_fi = financial_independence(average12, net_worth,
            withdrawl_rate, return_rate)

    # Export into csv file
    df_grouped.to_csv('output/grouped.csv', float_format='%1.2f')
    df_cats_by_date.to_csv('output/cats_by_date.csv', float_format='%1.2f')
    df_root_by_date.to_csv('output/root_by_date.csv', float_format='%1.2f')
    df_total_by_date.to_csv('output/total_by_date.csv', float_format='%1.2f')
    df_root_by_year.to_csv('output/root_by_year.csv', float_format='%1.2f')
    average12.to_csv('output/average12.csv', float_format='%1.2f')
    df_fi.to_csv('output/df_fi.csv', float_format='%1.2f')


if __name__ == '__main__':
    main(sys.argv[1:])
