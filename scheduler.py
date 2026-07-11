import schedule
import time
import pytz
from datetime import datetime
import main
import sys

# Schedule mapping: Day of week -> (Time (HH:MM), Topic)
# Times are provided in 24-hour format
SCHEDULE = {
    "monday": ("set-custom-time", "your-topic-here"),
    "tuesday": ("set-custom-time", "your-topic-here"),
    "wednesday": ("set-custom-time", "your-topic-here"),
    "thursday": ("set-custom-time", "your-topic-here"),
    "friday": ("set-custom-time", "your-topic-here"),
    "saturday": ("set-custom-time", "your-topic-here"),
    "sunday": ("set-custom-time", "your-topic-here"),
}

def job(topic):
    print(f"\n⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduled job triggered for topic: {topic}")
    try:
        main.main(topic)
    except Exception as e:
        print(f"❌ Error running automation for {topic}: {e}")

def run_scheduler(test_mode=False):
    if test_mode:
        print("🧪 Running in TEST mode. Triggering all jobs immediately...")
        for day, (t, topic) in SCHEDULE.items():
            job(topic)
        return

    print("📅 Setting up weekly schedule (US/Central Time)...")
    
    tz = "US/Central"
    
    try:
        schedule.every().monday.at(SCHEDULE["monday"][0], tz).do(job, SCHEDULE["monday"][1])
        schedule.every().tuesday.at(SCHEDULE["tuesday"][0], tz).do(job, SCHEDULE["tuesday"][1])
        schedule.every().wednesday.at(SCHEDULE["wednesday"][0], tz).do(job, SCHEDULE["wednesday"][1])
        schedule.every().thursday.at(SCHEDULE["thursday"][0], tz).do(job, SCHEDULE["thursday"][1])
        schedule.every().friday.at(SCHEDULE["friday"][0], tz).do(job, SCHEDULE["friday"][1])
        schedule.every().saturday.at(SCHEDULE["saturday"][0], tz).do(job, SCHEDULE["saturday"][1])
        schedule.every().sunday.at(SCHEDULE["sunday"][0], tz).do(job, SCHEDULE["sunday"][1])
    except Exception as e:
        print(f"⚠️ Error setting timezone in schedule: {e}")
        print("Fallback: Scheduling without timezone, jobs will run based on local system time.")
        schedule.every().monday.at(SCHEDULE["monday"][0]).do(job, SCHEDULE["monday"][1])
        schedule.every().tuesday.at(SCHEDULE["tuesday"][0]).do(job, SCHEDULE["tuesday"][1])
        schedule.every().wednesday.at(SCHEDULE["wednesday"][0]).do(job, SCHEDULE["wednesday"][1])
        schedule.every().thursday.at(SCHEDULE["thursday"][0]).do(job, SCHEDULE["thursday"][1])
        schedule.every().friday.at(SCHEDULE["friday"][0]).do(job, SCHEDULE["friday"][1])
        schedule.every().saturday.at(SCHEDULE["saturday"][0]).do(job, SCHEDULE["saturday"][1])
        schedule.every().sunday.at(SCHEDULE["sunday"][0]).do(job, SCHEDULE["sunday"][1])

    print("\n⏳ Scheduler is running... Press Ctrl+C to exit.")
    for job_desc in schedule.get_jobs():
        print(f"   - {job_desc}")

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    run_scheduler(test_mode)
