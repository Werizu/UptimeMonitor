#!/usr/bin/env python3
import json
import logging
import os
import signal
import sys
import time

import requests
import schedule

import database

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("uptime-monitor")

running = True
site_states = {}


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def send_pushover(config, title, message, priority=0):
    po = config["pushover"]
    if po["user_key"] == "YOUR_USER_KEY" or po["api_token"] == "YOUR_API_TOKEN":
        log.warning("Pushover not configured, skipping notification")
        return
    try:
        resp = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": po["api_token"],
                "user": po["user_key"],
                "title": title,
                "message": message,
                "priority": priority,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            log.info("Pushover notification sent: %s", title)
        else:
            log.error("Pushover failed (%d): %s", resp.status_code, resp.text)
    except Exception as e:
        log.error("Pushover error: %s", e)


def check_site(site, config):
    url = site["url"]
    name = site.get("name", url)
    timeout = config["defaults"]["timeout"]
    expected = config["defaults"]["expected_status"]

    status_code = None
    response_time_ms = None
    is_up = False

    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        status_code = resp.status_code
        response_time_ms = round(resp.elapsed.total_seconds() * 1000, 1)
        is_up = status_code == expected
    except requests.exceptions.Timeout:
        log.warning("%s: timeout after %ds", name, timeout)
    except requests.exceptions.RequestException as e:
        log.warning("%s: request failed — %s", name, e)

    database.log_check(url, status_code, response_time_ms, is_up)

    prev_state = site_states.get(url)

    if prev_state is None:
        # First check
        site_states[url] = is_up
        if not is_up:
            database.log_event(url, "DOWN")
            send_pushover(
                config,
                f"🔴 {name} is DOWN",
                f"{url}\nStatus: {status_code or 'no response'}",
                priority=1,
            )
    elif prev_state and not is_up:
        # Was UP, now DOWN
        site_states[url] = False
        database.log_event(url, "DOWN")
        send_pushover(
            config,
            f"🔴 {name} is DOWN",
            f"{url}\nStatus: {status_code or 'no response'}",
            priority=1,
        )
    elif not prev_state and is_up:
        # Was DOWN, now UP
        site_states[url] = True
        database.log_event(url, "UP")
        send_pushover(
            config,
            f"🟢 {name} is back UP",
            f"{url}\nResponse: {response_time_ms}ms",
            priority=0,
        )
    else:
        site_states[url] = is_up

    status_str = "UP" if is_up else "DOWN"
    log.info("%s: %s (code=%s, time=%sms)", name, status_str, status_code, response_time_ms)


def shutdown(signum, frame):
    global running
    log.info("Shutting down (signal %d)...", signum)
    running = False


def main():
    global running

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    config = load_config()
    database.init_db()

    log.info("Starting uptime monitor with %d site(s)", len(config["sites"]))

    default_interval = config["defaults"]["check_interval"]

    for site in config["sites"]:
        interval = site.get("check_interval", default_interval)
        schedule.every(interval).seconds.do(check_site, site=site, config=config)
        # Run first check immediately
        check_site(site, config)

    # Cleanup old data once a day
    schedule.every().day.at("03:00").do(database.cleanup_old_data)

    while running:
        schedule.run_pending()
        time.sleep(1)

    log.info("Monitor stopped.")


if __name__ == "__main__":
    main()
