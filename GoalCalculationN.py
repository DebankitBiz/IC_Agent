import pandas as pd
import numpy as np
import logging
import os
# import plotly.express as px
# import plotly.io as pio

# pio.renderers.default = 'browser'



# def previous_quarter_sales():
#     df = pd.read_excel('C:\IC Agents\crewai\icagents\Goal Setting sanitized Data.xlsx', sheet_name='Input Sales')  # Assuming header starts at row 4

#     # Clean column names
#     df.columns = df.columns
#     columns_to_sum = [
#         "Product 1 R12 Apr",
#         "Product 1 R12 May",
#         "Product 1 R12 Jun"
#     ]

#     df["Product 1 Q2"] = df[columns_to_sum].sum(axis=1)
#     df=df[["Territory", "Territory Name", "Product 1 Q2"]]
    
#     return df

def calculate_goals(national_goal: int, sales_file_path: str, min_growth: int, max_growth: int,product_weights: dict = None) -> pd.DataFrame:
    """
    Calculates IC goals using the national goal and input Excel data.
    
    Args:
        national_goal (int): The national goal as a whole number.
        sales_file_path (str): Path to the input Excel file.
        
    Returns:
        pd.DataFrame: A DataFrame containing the final goal calculation.
    """
    try:
        print(f"📌 National Goal received: {national_goal}")

        r12_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        products = ["Product 1", "Product 2", "Product 3"]
        if product_weights is None:
            product_weights = {"Product 2": 60, "Product 3": 40}
            
        Region_name = {
            101: "East Division",
            201: "West Division",
            301: "Central Division"
        }
       

        # Load Excel data
        df_sales = pd.read_excel(sales_file_path, sheet_name='Input Sales_Anomaly_Introduced')
        df_mapping = pd.read_excel(sales_file_path, sheet_name='1c. Inputs - Mappings', skiprows=5, usecols="C:D")
        df_mapping.drop_duplicates(inplace=True)

        # Merge mappings
        df = df_sales.merge(df_mapping, how="left", left_on="Territory", right_on="TS Territory")
        df.drop("TS Territory", axis=1, inplace=True)
        df["Region"] = df["Region"].astype(int)
        df["Region Name"] = df["Region"].map(Region_name)
        
        #print(df.head())
        

        # Calculate R12 totals
        for product in products:
            df[f"{product} R12 Total"] = df[[f"{product} R12 {month}" for month in r12_months]].sum(axis=1)

        df = df[["Region","Region Name", "Territory", "Territory Name"] + [f"{p} R12 Total" for p in products]]
        df['Baseline Goal'] = df[f'{products[0]} R12 Total'] / 2
        baseline_goal = df['Baseline Goal'].sum()
        
        for product in products[1:]:
            df[f"{product} Index"] = np.round(
                (df[f"{product} R12 Total"] / df[f"{product} R12 Total"].sum()) * 100, 1
            )

        df['Market Index'] = sum(df[f"{p} Index"] * product_weights[p] for p in products[1:])
        df['Market Index'] = np.round(df['Market Index'] / 100, 1)

        df["Growth/Potential Goal"] = np.round(abs(baseline_goal - national_goal) * df['Market Index'] / 100, 1)
        df["Preliminary Goal"] = df['Baseline Goal'] + df["Growth/Potential Goal"]
        df['Adjusted Preliminary Goal'] = np.round(
            (df["Preliminary Goal"] / df["Preliminary Goal"].sum()) * national_goal, 1
        )
        df['Growth%'] = (df['Adjusted Preliminary Goal'] / df['Baseline Goal'] - 1) * 100
       
        National_Growth=(df['Adjusted Preliminary Goal'].sum()/df['Baseline Goal'].sum())-1
        
        cap_min_terr_growth = National_Growth*min_growth*100
        cap_max_terr_growth = National_Growth*max_growth*100
        print(National_Growth, min_growth, max_growth)
        print(cap_min_terr_growth,cap_max_terr_growth)
        
        # Capping growth
        df['Capped Flag'] = np.where(
            df['Growth%'] < cap_min_terr_growth, 1,
            np.where(df['Growth%'] > cap_max_terr_growth, 2, 0)
        )
        df['Capped Growth%'] = df['Growth%'].clip(lower=cap_min_terr_growth, upper=cap_max_terr_growth)

        df['Initial Capped Goal'] = np.where(
            df['Baseline Goal'] == 0,
            df['Growth%'],
            (1 + df['Capped Growth%'] / 100) * df['Baseline Goal']
        )
        
        
        total_diff = max(0, df['Adjusted Preliminary Goal'].sum() - df['Initial Capped Goal'].sum())
        df['Spare growth'] = np.where(
            total_diff > 0,
            (cap_max_terr_growth / 100 - df['Capped Growth%'] / 100) * df['Baseline Goal'],
            (df['Capped Growth%'] / 100 - cap_min_terr_growth / 100) * df['Baseline Goal']
        )

        total_spare_growth = df['Spare growth'].sum()
        df["% of Nation"] = df['Spare growth'] / total_spare_growth * 100
        df["Goal Difference (Delta)"] = df["% of Nation"] * total_diff
        df["Final Goal (cartons)"] = np.round(df["Goal Difference (Delta)"] + df['Initial Capped Goal'], 0)
        df.to_excel("output\calculated_goals.xlsx",index=False)
        return df

    except Exception as e:
        print(f"Error calculating goals: {str(e)}")
        raise

# df=calculate_goals(5600, "C:\IC Agents\crewai\icagents\Goal Setting sanitized Data.xlsx",1.0,-1.0)
# print(df.columns)
# print(df)

# previous_df = previous_quarter_sales()

# # Merge with previous quarter data
# merged_df = df.merge(
#     previous_df[['Territory', 'Product 1 Q2']],
#     on='Territory',
#     how='inner'
# )

# # Calculate growth percentage
# merged_df['Growth (%)'] = ((merged_df["Final Goal (cartons)"] - merged_df['Product 1 Q2']) /
#                         merged_df['Product 1 Q2']) * 100

# # Sort descending by growth
# merged_df = merged_df.sort_values(by='Growth (%)', ascending=False)
# fig = px.bar(merged_df, x='Territory Name', y='Growth (%)', title="Quarter-over-Quarter Growth")

# # fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
# # fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

# # Show chart
# fig.show()