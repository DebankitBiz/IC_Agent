import pandas as pd
def detect_product1_anomalies_dynamic(sales_df: pd.DataFrame, z_thresh: float = -2.0) -> pd.DataFrame:
    """
    Detects anomalies in Product 1 sales (Jan–Jun) using z-score thresholding.

    Parameters:
    - sales_df: pd.DataFrame with Product 1 R12 Jan–Jun columns
    - z_thresh: float, the z-score below which a value is flagged as anomaly (default -2.0)

    Returns:
    - pd.DataFrame with anomalies including z-score
    """
    target_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    product1_cols = [f"Product 1 R12 {m}" for m in target_months]

    # Check for missing columns
    missing = [col for col in product1_cols if col not in sales_df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    # Melt to long format
    df_long = sales_df.melt(
        id_vars=["Territory", "Territory Name"],
        value_vars=product1_cols,
        var_name="Month",
        value_name="Sales"
    )
    df_long["Month"] = df_long["Month"].str.extract(r'R12 (\w+)', expand=False)

    # Compute z-scores by month
    stats = df_long.groupby("Month")["Sales"].agg(["mean", "std"]).reset_index()
    df_merged = df_long.merge(stats, on="Month")
    df_merged["z_score"] = (df_merged["Sales"] - df_merged["mean"]) / df_merged["std"]

    # Flag anomalies below z-score threshold
    anomalies = df_merged[df_merged["z_score"] < z_thresh].copy()
    anomalies = anomalies[["Territory", "Territory Name", "Month", "Sales", "z_score"]].reset_index(drop=True)
    
    return anomalies

def cross_verify_anomalies_with_fema(anomalies_df: pd.DataFrame, fema_df: pd.DataFrame) -> pd.DataFrame:
    """
    Matches anomalies to FEMA disasters by comparing territory and month.

    Parameters:
    - anomalies_df: DataFrame with at least ['Territory', 'Territory Name', 'Month', 'Sales', 'z_score']
    - fema_df: FEMA DataFrame with at least ['TS Territory ID', 'IncidentBeginDate', 'IncidentEndDate', 'IncidentType', 'DeclarationTitle']

    Returns:
    - pd.DataFrame with FEMA match results and a 'Disaster Match' flag
    """

    # 1. Normalize month format in anomalies
    month_map = {
        "Jan": "January", "Feb": "February", "Mar": "March",
        "Apr": "April", "May": "May", "Jun": "June",
        "Jul": "July", "Aug": "August", "Sep": "September",
        "Oct": "October", "Nov": "November", "Dec": "December"
    }
    anomalies_df = anomalies_df.copy()
    anomalies_df["IncidentMonth"] = anomalies_df["Month"].map(month_map)

    # 2. Prepare FEMA data
    fema_df = fema_df.copy()
    fema_df["IncidentBeginDate"] = pd.to_datetime(fema_df["IncidentBeginDate"], errors="coerce")
    fema_df["IncidentEndDate"] = pd.to_datetime(fema_df["IncidentEndDate"], errors="coerce")
    fema_df["IncidentMonth"] = fema_df["IncidentBeginDate"].dt.strftime("%B")
    fema_df["TS Territory ID"] = pd.to_numeric(fema_df["TS Territory ID"], errors="coerce").astype("Int64")

    # 3. Group FEMA incidents by Territory and Month, and get min/max dates + type/title
    fema_grouped = fema_df.groupby(["TS Territory ID", "IncidentMonth"]).agg({
        "IncidentBeginDate": "min",
        "IncidentEndDate": "max",
        "IncidentType":"first",
        "DeclarationTitle":"first"
    }).reset_index()

    # 4. Merge with anomalies
    merged = anomalies_df.merge(
        fema_grouped,
        how="left",
        left_on=["Territory", "IncidentMonth"],
        right_on=["TS Territory ID", "IncidentMonth"]
    )

    # 5. Flag match
    merged["Disaster Match"] = ~merged["IncidentType"].isna()
    merged.drop_duplicates(inplace=True)
    merged["DisasterDuration"] = (merged["IncidentEndDate"] - merged["IncidentBeginDate"]).dt.days
    merged = merged[merged["DisasterDuration"] > 12]

    return merged
def format_disaster_impact_summary_html(verified_anomalies_df: pd.DataFrame, sales_df: pd.DataFrame) -> str:
    """
    Generate a detailed HTML summary of anomalies with disaster impact,
    inside a fully-rounded, oval-styled container consistent with bot messages.
    """

    disaster_rows = verified_anomalies_df[verified_anomalies_df["Disaster Match"] == True]

    if disaster_rows.empty:
        return """
        <div style='
            display: flex;
            align-items: flex-start;
            background-color: #fff8dc;
            border-radius: 2rem;
            padding: 1rem 1.5rem;
            max-width: 80%;
            margin: 1rem 0;
        '>
            <div class='icon bot-icon' style='
                width: 30px;
                height: 30px;
                margin-right: 10px;
                background-color: #ffc107;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
            '>🤖</div>
            <div>
                ✅ No disasters were detected that impacted your sales data. Goal calculation proceeded normally.
            </div>
        </div>
        """

    # Melt sales data into long format
    target_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    product1_cols = [f"Product 1 R12 {m}" for m in target_months]

    df_long = sales_df.melt(
        id_vars=["Territory", "Territory Name"],
        value_vars=product1_cols,
        var_name="Month",
        value_name="Sales"
    )
    df_long["Month"] = df_long["Month"].str.extract(r'R12 (\w+)', expand=False)

    # Message container with fully rounded edge
    message = """
    <div style='
        display: flex;
        align-items: flex-start;
        background-color: #fff8dc;
        border-radius: 2rem;
        padding: 1rem 1.5rem;
        max-width: 100%;
        margin: 1rem 0;
    '>
        
        <div>
            <p>⚠️ <strong>While analyzing your sales data, we detected FEMA-confirmed disasters that likely impacted performance.</strong></p>
            <h4>🧾 Impact Summary:</h4>
    """

    impacted_months = []

    for _, row in disaster_rows.iterrows():
        territory = row["Territory"]
        territory_name = row["Territory Name"]
        month = row["Month"]
        anomalous = row["Sales"]

        peer_sales = df_long[
            (df_long["Territory"] == territory) & (df_long["Month"] != month)
        ]["Sales"]
        avg_other = peer_sales.mean()
        drop_units = anomalous - avg_other
        drop_pct = (drop_units / avg_other * 100) if avg_other > 0 else None

        disaster = f"{row.get('IncidentType', 'Unknown')} — {row.get('DeclarationTitle', 'Unknown')}"
        begin = pd.to_datetime(row.get("IncidentBeginDate")).strftime("%B %d") if pd.notnull(row.get("IncidentBeginDate")) else "Unknown"
        end = pd.to_datetime(row.get("IncidentEndDate")).strftime("%d, %Y") if pd.notnull(row.get("IncidentEndDate")) else "Unknown"

        message += f"""
            <div style='margin-bottom: 1.2rem; padding-left: 1rem;'>
                <p><strong>📍 Territory:</strong> {territory_name}</p>
                <ul style='margin: 0.2rem 0 0.2rem 1rem;'>
                    <li>📅 <strong>Month:</strong> {month}</li>
                    <li>🎯 <strong>Anomalous Goal:</strong> {anomalous}</li>
                    <li>📊 <strong>Average of Other Months:</strong> {avg_other:.1f}</li>
                    <li>📉 <strong>Drop from Trend:</strong> {drop_units:.1f} units (⬇️ {drop_pct:.1f}%)</li>
                    <li>🌪️ <strong>Disaster Impact:</strong> {disaster}</li>
                    <li>🗓️ <strong>Disaster Period:</strong> {begin}–{end}</li>
                </ul>
                <p style='margin-top: 0.5rem;'>📊 <em>We may exclude {month} from baseline calculations to ensure fair, achievable goals.</em></p>
            </div>
        """

        impacted_months.append(month)

    joined_months = ", ".join(sorted(set(impacted_months)))
    message += f"""
            <hr style='margin: 1.5rem 0;' />
            <p><strong>✅ Would you like to exclude these disaster-affected months ({joined_months}) from the baseline to proceed with a fair goal calculation?</strong></p>
        </div>
    </div>
    """

    return message




#sales_df=pd.read_excel("C:\IC Agents\crewai\icagents\Goal Setting sanitized Data.xlsx", sheet_name='Input Sales_Anomaly_Introduced')
#anomalies_df=detect_product1_anomalies_dynamic(sales_df,  -2.0)
#print(anomalies_df)
#fema_df=pd.read_excel("C:\IC Agents\crewai\icagents\ZIP_to_Territory_with_FEMA_Data.xlsx",sheet_name="2025_ZIP_to_Territory")
#cause_df=cross_verify_anomalies_with_fema(anomalies_df, fema_df)
#print(cause_df)
#summary_df=format_disaster_impact_summary_html(cause_df,sales_df)
#print(summary_df)
