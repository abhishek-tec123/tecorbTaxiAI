from prophet import Prophet
from sklearn.metrics import mean_absolute_percentage_error
import pandas as pd
from sqlalchemy import create_engine
from data import get_weekly_hourly_driver_counts

def forecast_next_monday(df, date_col, value_col):
    prophet_df = df.rename(columns={date_col: "ds", value_col: "y"})
    prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])

    m = Prophet(weekly_seasonality=True, yearly_seasonality=False,
                daily_seasonality=False, seasonality_mode="multiplicative")
    m.fit(prophet_df)

    future = m.make_future_dataframe(periods=1, freq="W-MON")
    forecast = m.predict(future)

    next_monday_forecast = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(1)

    y_true = prophet_df["y"]
    y_pred = m.predict(prophet_df)["yhat"]
    mape = mean_absolute_percentage_error(y_true, y_pred) * 100
    confidence_score = 100 - mape

    print("Next Monday Forecast:")
    print(next_monday_forecast)
    print(f"\nEstimated Confidence Score: {confidence_score:.2f}%")
    print(f"Mean Absolute Percentage Error (MAPE): {mape:.2f}%")

    return next_monday_forecast

engine = create_engine("mysql+pymysql://root:root%40123@localhost:3306/taxiProduction")
df_weekly_driver = get_weekly_hourly_driver_counts(engine, hour=12, start_date='2025-07-07', end_date='2025-11-17')
print("dataframe is : ", df_weekly_driver)
df_for_forcst = df_weekly_driver[:-1]

value = forecast_next_monday(df_for_forcst, date_col="report_date", value_col="total_count")

# # forecast for all hour of next date---------------------------------------------------

# from prophet import Prophet
# from sklearn.metrics import mean_absolute_percentage_error
# import pandas as pd


# def forecast_next_monday_per_hour(df, date_col, value_col, hour_col):
#     results = []

#     for hour in sorted(df[hour_col].unique()):
#         df_hour = df[df[hour_col] == hour].copy()

#         if len(df_hour) < 3:
#             continue  # Prophet needs enough data

#         prophet_df = df_hour.rename(
#             columns={date_col: "ds", value_col: "y"}
#         )
#         prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])

#         m = Prophet(
#             weekly_seasonality=True,
#             yearly_seasonality=False,
#             daily_seasonality=False,
#             seasonality_mode="multiplicative"
#         )
#         m.fit(prophet_df)

#         future = m.make_future_dataframe(periods=1, freq="W-MON")
#         forecast = m.predict(future)

#         next_forecast = forecast.tail(1)

#         # Confidence calculation
#         y_true = prophet_df["y"]
#         y_pred = m.predict(prophet_df)["yhat"]
#         mape = mean_absolute_percentage_error(y_true, y_pred) * 100
#         confidence_score = 100 - mape

#         results.append({
#             "hour": hour,
#             "forecast_date": next_forecast["ds"].iloc[0],
#             "yhat": next_forecast["yhat"].iloc[0],
#             "yhat_lower": next_forecast["yhat_lower"].iloc[0],
#             "yhat_upper": next_forecast["yhat_upper"].iloc[0],
#             "mape": mape,
#             "confidence_score": confidence_score
#         })

#     return pd.DataFrame(results)

# engine = create_engine(
#     "mysql+pymysql://root:root%40123@localhost:3306/taxiProduction"
# )

# df_weekly_driver = get_weekly_hourly_driver_counts(
#     engine,
#     start_date="2025-07-07",
#     end_date="2025-11-17"
# )

# # Remove last known week to avoid leakage
# df_for_forecast = df_weekly_driver[:-24]

# forecast_df = forecast_next_monday_per_hour(
#     df=df_for_forecast,
#     date_col="report_date",
#     value_col="total_count",
#     hour_col="hour"
# )

# print(forecast_df)

