# import pandas as pd
# from sqlalchemy import text, create_engine

# def get_weekly_hourly_driver_counts(engine, hour, start_date, end_date):

#     query = text("""
#     SELECT report_date, total_count
#     FROM driver_hourly_counts
#     WHERE hour = :hour
#       AND report_date BETWEEN :start_date AND :end_date
#       AND MOD(DATEDIFF(report_date, :start_date), 7) = 0
#     ORDER BY report_date
#     """)
    
#     with engine.connect() as conn:
#         df = pd.read_sql(query, conn, params={
#             "hour": hour,
#             "start_date": start_date,
#             "end_date": end_date
#         })
    
#     return df

# def get_weekly_hourly_rider_counts(engine, hour, start_date, end_date):

#     query = text("""
#     SELECT report_date, total_count
#     FROM rider_hourly_counts
#     WHERE hour = :hour
#       AND report_date BETWEEN :start_date AND :end_date
#       AND MOD(DATEDIFF(report_date, :start_date), 7) = 0
#     ORDER BY report_date
#     """)
    
#     with engine.connect() as conn:
#         df = pd.read_sql(query, conn, params={
#             "hour": hour,
#             "start_date": start_date,
#             "end_date": end_date
#         })
    
#     return df

# # # Example usage
# # if __name__ == "__main__":
# #     engine = create_engine("mysql+pymysql://root:root%40123@localhost:3306/taxiProduction")

# #     df_weekly_driver = get_weekly_hourly_driver_counts(engine, hour=9, start_date='2025-07-07', end_date='2025-11-17')
# #     print("driver_count")
# #     print(df_weekly_driver)

#     # df_weekly_rider = get_weekly_hourly_rider_counts(engine, hour=10, start_date='2025-07-07', end_date='2025-11-17')
#     # print("rider_count")
#     # print(df_weekly_rider)

# collect rider driver data hourly------------------------------------------------------------------------------------

