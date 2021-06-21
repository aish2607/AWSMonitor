import argparse
import dateutil.relativedelta as dateutil
import datetime
import os
import sys

import boto3
import botocore.exceptions

DATETIME_NOW = datetime.datetime.utcnow() #gives todays date and time
AWS_COST_EXPLORER_SERVICE_KEY = "ce"
#OUTPUT_FILE_NAME = "report"+str(DATETIME_NOW).replace(':','-')+".csv"
OUTPUT_FILE_NAME = "report.csv"
DEFAULT_PROFILE_NAME = "default"
OUTPUT_FILE_HEADER_LINE = ",".join(
    ["Time Period", "Linked Account", "Service", "Amount",
     "Unit", "Estimated", "\n"]) #joins the follow with commas separated
CURRENT_FOLDER_PATH = os.path.abspath(os.path.curdir) #gives the path of the directory this file is in
DEFAULT_OUTPUT_FILE_PATH = os.path.join(CURRENT_FOLDER_PATH, OUTPUT_FILE_NAME)
COST_EXPLORER_GRANULARITY_MONTHLY = "MONTHLY"
COST_EXPLORER_GRANULARITY_DAILY = "DAILY"
COST_EXPLORER_GROUP_BY = [
    {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"},
    {"Type": "DIMENSION", "Key": "SERVICE"}]


def main():
    daily, monthly, enable_total, output_file, profile_name = process_args(
        create_parser())
    try:
        session = boto3.Session(profile_name=profile_name,aws_access_key_id='AKIAXMDA4XYCI2GPHRBU', aws_secret_access_key='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')
    except botocore.exceptions.ProfileNotFound as exp:
        print("Error: %s" % str(exp))
        sys.exit(1)
    cost_explorer = session.client(AWS_COST_EXPLORER_SERVICE_KEY)
    granularity = COST_EXPLORER_GRANULARITY_MONTHLY
    if daily:
        granularity = COST_EXPLORER_GRANULARITY_DAILY
    write_output_file(
        output_file,
        get_cost_and_usage(
            cost_explorer,
            granularity,
            daily,
            monthly),
        enable_total,
        monthly)
    print("\nOutput written to: %s" % output_file)


def process_args(parser):
    args = parser.parse_args()
    days, months = args.days, args.months
    if (type(days) is int) and (type(months) is int):
        parser.print_help()
        print("Error: 'days' and 'months' options are mutually exclusive.")
        sys.exit(1)
    if days is None and months is None:
        days, months = 0, 1
    output_fpath = args.fpath
    enable_total = not args.disable_total
    profile_name = args.profile_name
    return days, months, enable_total, output_fpath, profile_name


def create_parser():
    parser = argparse.ArgumentParser(
        description="AWS Simple Cost and Usage Report")
    parser.add_argument(
        "--output",
        dest="fpath",
        default=DEFAULT_OUTPUT_FILE_PATH,
        help="output file path (default:%s)" % OUTPUT_FILE_NAME)
    parser.add_argument(
        "--profile-name",
        dest="profile_name",
        default=DEFAULT_PROFILE_NAME,
        help="Profile name on your AWS account (default:%s)" %
        DEFAULT_PROFILE_NAME)
    parser.add_argument(
        "--days",
        type=int,
        dest="days",
        default=None,
        help="get data for daily usage and cost by given days.\
             (Mutualy exclusive with 'months' option, default: 0)")
    parser.add_argument(
        "--months",
        type=int,
        dest="months",
        default=None,
        help="get data for monthly usage and cost by given months. \
             (Mutualy exclusive with 'days' option, default: 1)")
    parser.add_argument(
        "--disable-total",
        action="store_true",
        default=False,
        help="Do not output total cost per day, or month unit.")
    return parser


def get_cost_and_usage(cost_explorer, granularity, days, months):
    time_period = {
        "Start": get_cost_start_period(days, months),
        "End": DATETIME_NOW.strftime("%Y-%m-%d")}
    token = None
    result = []
    while True:
        kwargs = {}
        if token:
            kwargs = {"NextPageToken": token}
        data = cost_explorer.get_cost_and_usage(
            TimePeriod=time_period,
            Granularity=granularity,
            Metrics=["UnblendedCost"],
            GroupBy=COST_EXPLORER_GROUP_BY, **kwargs)
        result += data["ResultsByTime"]
        token = data.get("NextPageToken", None)
        if not token:
            break
    return result


def get_cost_start_period(days, months):
    start_strftime = None
    if months:
        if months == 1:
            start_strftime = DATETIME_NOW.strftime("%Y-%m-01")
        else:
            prev_month = DATETIME_NOW - dateutil.relativedelta(months=months - 1)
            start_strftime = prev_month.strftime("%Y-%m-01")
    if days:
        prev_day = DATETIME_NOW - datetime.timedelta(days=days)
        start_strftime = prev_day.strftime("%Y-%m-%d")
    return start_strftime


def write_output_file(output_file, cost_and_usage_data, enable_total, monthly):
    with open(output_file, "w") as output_file_:
        write_output("#" + OUTPUT_FILE_HEADER_LINE, output_file_)
        for cost_and_usage_by_time in cost_and_usage_data:
            total_cost = 0
            for cost_group_data in cost_and_usage_by_time["Groups"]:
                cost_group = CostGroup(
                    cost_group_data, cost_and_usage_by_time, monthly)
                write_output(str(cost_group), output_file_)
                total_cost += float(cost_group.amount)
            if enable_total:
                total_msg = "Total Cost: %s,,,,,\n" % str(total_cost)
                write_output(total_msg, output_file_)


def write_output(msg, output_file, reflect_to_stdout=True):
    if reflect_to_stdout:
        print(msg.strip())
    output_file.write(msg)


class CostGroup():
    """ Class that abstracts a cost group. Will allow us to have shorter
    and more simple functions by going to the essence of the concept."""

    def __init__(self, cost_group_data, cost_and_usage_by_time, is_monthly):
        self.account_id = cost_group_data["Keys"][0]
        self.service = cost_group_data["Keys"][1]
        self.time_start = cost_and_usage_by_time["TimePeriod"]["Start"]
        if is_monthly:
            date_parts = self.time_start.split("-")
            self.time_start = "%s/%s" % (date_parts[1], date_parts[0])
        self.amount = cost_group_data["Metrics"]["UnblendedCost"]["Amount"]
        self.unit = cost_group_data["Metrics"]["UnblendedCost"]["Unit"]
        self.estimated = cost_and_usage_by_time["Estimated"]

    def __repr__(self):
        return "%s, %s, %s, %s, %s, %s\n" % (
            self.time_start,
            self.account_id,
            self.service,
            self.amount,
            self.unit,
            self.estimated)


if __name__ == "__main__":
    main()