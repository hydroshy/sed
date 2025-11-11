#!/usr/bin/env python3
"""
Log Analysis Tool: Count Actual Job Executions vs PiCamera2 Background Jobs

Usage:
    python3 analyze_job_logs.py <logfile.txt>

This script helps distinguish between:
1. Your application job pipeline executions (what we throttle)
2. PiCamera2 background frame capture jobs (not throttled)
"""

import sys
import re
from datetime import datetime, timedelta

def parse_timestamp(ts_str):
    """Parse timestamp like '2025-11-02 11:04:06,782'"""
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S,%f")
    except:
        return None

def analyze_logs(filename):
    """Analyze log file and categorize job executions"""
    
    app_jobs = []  # [CameraManager] EXECUTING JOB PIPELINE
    picam_jobs = []  # picamera2.picamera2 - DEBUG - Execute job
    detect_jobs = []  # tools.detection.detect_tool - INFO - DetectTool found
    
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Parse timestamp at start of line
            match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
            if not match:
                continue
                
            ts_str = match.group(1)
            ts = parse_timestamp(ts_str)
            if not ts:
                continue
            
            # Check line type
            if '[CameraManager] EXECUTING JOB PIPELINE' in line:
                # Extract interval from: "interval=0.3772s"
                interval_match = re.search(r'interval=([\d.]+)s', line)
                interval = float(interval_match.group(1)) if interval_match else None
                app_jobs.append({
                    'time': ts,
                    'interval': interval,
                    'line': line.strip()
                })
            elif 'picamera2.picamera2 - DEBUG - Execute job:' in line:
                picam_jobs.append({
                    'time': ts,
                    'line': line.strip()
                })
            elif 'tools.detection.detect_tool - INFO - ✔️ DetectTool found' in line or \
                 'tools.detection.detect_tool - INFO - âœ… DetectTool found' in line:
                detect_jobs.append({
                    'time': ts,
                    'line': line.strip()
                })
    
    return app_jobs, picam_jobs, detect_jobs

def print_analysis(app_jobs, picam_jobs, detect_jobs):
    """Print detailed analysis"""
    
    print("=" * 80)
    print("JOB EXECUTION ANALYSIS")
    print("=" * 80)
    
    # Application Jobs
    print(f"\n📊 APPLICATION JOB EXECUTIONS: {len(app_jobs)} total")
    print("-" * 80)
    
    if app_jobs:
        print(f"{'#':<4} {'Time':<23} {'Interval':<12} {'Status':<10}")
        print("-" * 80)
        
        for i, job in enumerate(app_jobs, 1):
            interval_str = f"{job['interval']:.4f}s" if job['interval'] else "N/A"
            status = "✓ EXECUTE" if (job['interval'] is None or job['interval'] >= 0.2) else "✗ THROTTLE"
            
            print(f"{i:<4} {job['time'].strftime('%H:%M:%S,%f')[:-3]:<23} {interval_str:<12} {status:<10}")
        
        # Statistics
        if len(app_jobs) > 1:
            intervals = [j['interval'] for j in app_jobs if j['interval']]
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                min_interval = min(intervals)
                max_interval = max(intervals)
                
                print("-" * 80)
                print(f"Average interval: {avg_interval:.4f}s")
                print(f"Min interval:     {min_interval:.4f}s")
                print(f"Max interval:     {max_interval:.4f}s")
                print(f"Threshold:        0.2000s (5 FPS)")
                
                # Throttle effectiveness
                throttled = sum(1 for i in intervals if i < 0.2)
                executed = len(intervals) - throttled
                print(f"\n✓ Jobs executed (≥0.2s): {executed}")
                print(f"✗ Jobs throttled (<0.2s): {throttled}")
                print(f"Throttle effectiveness: {(throttled/len(intervals)*100):.1f}%")
    
    # PiCamera2 Background Jobs
    print(f"\n\n🎥 PICAMERA2 BACKGROUND JOBS: {len(picam_jobs)} total")
    print("-" * 80)
    print(f"These are camera frame capture operations (normal)")
    print(f"Happen during GPU inference")
    print(f"NOT part of job throttling")
    
    if picam_jobs and len(app_jobs) > 0:
        # Find background jobs during first app job
        first_app_start = app_jobs[0]['time']
        if len(app_jobs) > 1:
            first_app_end = app_jobs[1]['time']
        else:
            first_app_end = first_app_start + timedelta(seconds=0.5)
        
        bg_during_first = [j for j in picam_jobs 
                          if first_app_start <= j['time'] <= first_app_end]
        
        print(f"\nBackground jobs during first app job: {len(bg_during_first)}")
        if bg_during_first:
            print(f"Time span: {bg_during_first[0]['time'].strftime('%H:%M:%S,%f')[:-3]} to "
                  f"{bg_during_first[-1]['time'].strftime('%H:%M:%S,%f')[:-3]}")
            duration = (bg_during_first[-1]['time'] - bg_during_first[0]['time']).total_seconds()
            print(f"Duration: {duration:.3f}s")
    
    # Detection Results
    print(f"\n\n🔍 DETECTION RESULTS: {len(detect_jobs)} total")
    print("-" * 80)
    
    if detect_jobs:
        for i, job in enumerate(detect_jobs, 1):
            print(f"{i}. {job['time'].strftime('%H:%M:%S,%f')[:-3]} - {job['line']}")
    
    # Summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    jobs_per_second = len(app_jobs) / max(1, (app_jobs[-1]['time'] - app_jobs[0]['time']).total_seconds()) if len(app_jobs) > 1 else 0
    
    print(f"\n✓ Application job executions: {len(app_jobs)}")
    print(f"✓ Jobs per second: {jobs_per_second:.1f} FPS (target: ~5 FPS)")
    print(f"✓ Throttle threshold: 0.2s")
    print(f"✓ Background camera jobs: {len(picam_jobs)} (normal)")
    print(f"\n{'✅ THROTTLE IS WORKING CORRECTLY!' if jobs_per_second <= 5.5 else '⚠️  THROTTLE MAY NEED ADJUSTMENT'}")
    
    if jobs_per_second > 5.5:
        print(f"   Current: {jobs_per_second:.1f} jobs/sec (exceeds 5 FPS target)")
        print(f"   Recommend: Increase throttle from 0.2s to 0.25-0.3s")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_job_logs.py <logfile.txt>")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    try:
        app_jobs, picam_jobs, detect_jobs = analyze_logs(filename)
        print_analysis(app_jobs, picam_jobs, detect_jobs)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
