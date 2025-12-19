import pandas as pd
from sqlalchemy import create_engine, text

# Create DB connection
engine = create_engine(
    "mysql+pymysql://root:root%40123@localhost:3306/taxiProduction"
)

def get_driver_hourly_counts_by_date(engine, report_date):
    query = text("""
        SELECT
            report_date,
            hour,
            total_count AS driver_total_count
        FROM driver_hourly_counts
        WHERE report_date = :report_date
        ORDER BY hour
    """)
    return pd.read_sql(query, engine, params={"report_date": report_date})

def get_rider_hourly_counts_by_date(engine, report_date):
    query = text("""
        SELECT
            report_date,
            hour,
            total_count AS rider_total_count
        FROM rider_hourly_counts
        WHERE report_date = :report_date
        ORDER BY hour
    """)
    return pd.read_sql(query, engine, params={"report_date": report_date})

if __name__ == "__main__":
    report_date = "2025-11-17"

    df_driver = get_driver_hourly_counts_by_date(engine, report_date)
    df_rider = get_rider_hourly_counts_by_date(engine, report_date)

    # Merge on report_date and hour
    df_combined = pd.merge(
        df_driver,
        df_rider,
        on=["report_date", "hour"],
        how="outer"
    ).sort_values("hour")

    # Optional: fill missing values
    df_combined[["driver_total_count", "rider_total_count"]] = (
        df_combined[["driver_total_count", "rider_total_count"]].fillna(0).astype(int)
    )

    print(df_combined)
