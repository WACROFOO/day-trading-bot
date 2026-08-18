<!-- source: https://support.warriortrading.com/support/solutions/articles/19000176267-simulator-performance-latency-troubleshooting-guide -->
<!-- category: Using the Warrior Trading Platform (Day Trade Dash, Community, and Simulator) -->
<!-- folder: Web Simulator (New!) -->
<!-- modified: Thu, Jul 23, 2026 at 3:29 PM -->

# Simulator Performance & Latency Troubleshooting Guide

Experiencing lag, sluggishness, or slow loading in the simulator? You may notice delays when loading widgets, updating charts, or navigating the platform. The good news is that most performance issues can be resolved once the cause is identified. Follow the steps below to diagnose and improve your experience.

TABLE OF CONTENTS

- [System Requirements and Recommendations](#System-Requirements-and-Recommendations)
- [Step 1: Sync Your Computer Clock](#Step-1%3A-Sync-Your-Computer-Clock)

[Windows 11](#Windows-11)
- [Mac OS](#Mac-OS)
- [Step 2: Power & Performance Settings](#Step-2%3A-Power-&-Performance-Settings)

[Windows 11 (Windows 11 only — lower versions are not supported)](#Windows-11%C2%A0(Windows-11-only-%E2%80%94-lower-versions-are-not-supported))
- [Mac OS (macOS Sonoma; M1 chip or later recommended)](#Mac-OS%C2%A0(macOS-Sonoma;-M1-chip-or-later-recommended))
- [Step 3: Network & Connection](#Step-3%3A-Network-&-Connection)

[Use a Wired Connection (Highest Priority)](#Use-a-Wired-Connection-(Highest-Priority))
- [Run a Speed Test](#Run-a-Speed-Test)
- [Reset Your Router/Modem](#Reset-Your-Router/Modem)
- [Step 4: VPN Settings](#Step-4%3A-VPN-Settings)
- [Step 5: Peak Hours & Bandwidth Usage](#Step-5%3A-Peak-Hours-&-Bandwidth-Usage)

[Close Bandwidth-Heavy Applications](#Close-Bandwidth-Heavy-Applications)
- [Step 6: Firewall & Antivirus](#Step-6%3A-Firewall-&-Antivirus)
- [Step 7: Browser & CPU Optimization](#Step-7%3A-Browser-&-CPU-Optimization)

[General Browser Tips](#General-Browser-Tips)
- [Monitor CPU Usage with the Browser Task Manager](#Monitor-CPU-Usage-with-the-Browser-Task-Manager)
[How to Open the Browser Task Manager](#How-to-Open-the-Browser-Task-Manager)
- [What to Do Once It's Open](#What-to-Do-Once-It's-Open)
- [Step 8: General System Maintenance](#Step-8%3A-General-System-Maintenance)
- [Quick Checklist Summary](#Quick-Checklist-Summary)
- [Still experiencing issues? ](#Still-experiencing-issues?%C2%A0)

## System Requirements and Recommendations

Before you dive into the troubleshooting steps below, first make sure your trading station meets the hardware requirements and recommendations below:

Computer (Hardware) Recommended Specifications:
• Processor:  16 Cores / 24 Threads (or more)
• Memory: Minimum 32 GB of RAM 
• Operating System: 64-bit Windows 11, or Latest MacOS
• Monitor Resolution: 2560 × 1440 (2k)  or 3840x2160 (4k UHD) 
• Hard Drive: 100GB free space
• Internet: minimum 100 Mbps download speed and at least 15 Mbps upload speed
• Suggested Minimum Ping Time: 20-50ms

Important Notice: The Minimum Computer Specifications listed below can adequately support a simple setup, like 1-2 monitors and a limited use of widgets and pop out windows. If you begin to notice a delay or latency in your experience, you will need to reduce the number of pop out windows and widgets or upgrade your computer system to the Recommended Specifications listed above. 

Minimum Computer Specifications:
• Processor:  8 Cores / 16 Threads
• Memory: Minimum 16 GB of RAM 
• Operating System: 64-bit Windows 11, or Latest MacOS
• Monitor Resolution: 1920 x 1080
• Hard Drive: 50GB free space
• Internet: minimum 50 Mbps download speed and at least 10 Mbps upload speed
• Suggested Minimum Ping Time: 20-50ms

To find processor core/threads, check the computer manufacturer's site, which will list all computer specs, including processor model, i.e., (Intel® Core™ Ultra 9 275HX). A Google search on the chip name for total cores and total threads will also help to identify these numbers.

Learn how to look up your system hardware and network through [our guide here.](https://support.warriortrading.com/support/solutions/articles/19000097233-check-computer-specifications)

## Step 1: Sync Your Computer Clock

An out-of-sync system clock can cause authentication failures, data feed errors, and platform instability. We recommend verifying your clock is accurate before troubleshooting further.

#### Windows 11

- 
Press Windows + I to open Settings
- 
Navigate to Time & Language → Date & Time
- 
Make sure the following are both turned ON:

Set time automatically
- 
Set time zone automatically
- 
Scroll down and click Sync now under the Additional settings section
- 
Confirm the Last successful time synchronization timestamp updates
Tip: If the sync fails, ensure you are connected to the internet and try again.

#### Mac OS

- 
Click the Apple menu () in the top-left corner
- 
Go to System Settings (or System Preferences on older macOS versions)
- 
Click General → Date & Time
- 
Enable Set time and date automatically
- 
Ensure the time server is set to Apple (time.apple.com) or Apple Americas/U.S.
- 
Close settings — your clock will now stay in sync automatically
Tip: If the option is grayed out, click the lock icon in the bottom-left and enter your admin password to make changes.

## Step 2: Power & Performance Settings

Running on low-power or efficiency mode can significantly impact simulator performance.

#### Windows 11 (Windows 11 only — lower versions are not supported)

- 
Press Windows + I to open Settings
- 
Navigate to System → Power & Battery
- 
Under Power Mode, select the appropriate setting:

| 
Power State | 
Recommended Setting
| 
Plugged In | 
Best Performance
| 
On Battery | 
Balanced (or Best Power Efficiency if extended unplugged use is needed)
Note: Selecting Best Performance on battery will reduce battery run time significantly.

#### Mac OS (macOS Sonoma; M1 chip or later recommended)

- 
Power Low Power Mode: Always OFF 
- 
Automatic Graphics Switching: OFF (MacBook Pro)
- 
Prevent App Nap: Enabled for Browsers/Trading Apps
- 
Display Sleep: Never
- 
Computer Sleep: Never
- 
Browser Throttling: Disabled

## Step 3: Network & Connection

The majority of performance issues are resolved by improving your network connection.

#### Use a Wired Connection (Highest Priority)

- 
Connect your computer directly to your router using an Ethernet cable
- 
Wi-Fi is susceptible to interference and instability — a wired connection is strongly preferred

#### Run a Speed Test

- 
Visit[ speedtest.net](https://www.speedtest.net)
- 
Minimum recommended speeds:

⬇️ Download: 50 Mbps
- 
⬆️ Upload: 30 Mbps
- 
If speeds are below these thresholds, contact your ISP

#### Reset Your Router/Modem

- 
Unplug both your router and modem
- 
Wait 30 seconds
- 
Plug the modem back in first — wait 1 minute
- 
Plug the router back in and wait for a full connection

## Step 4: VPN Settings

VPNs can either help or hurt performance depending on your location.

- 
If you are using a VPN: Try disconnecting temporarily to see if performance improves
- 
If you are NOT using a VPN and are located far from the US East Coast: Consider trying[ NordVPN](https://nordvpn.com) (free trial available) and connecting through a New York server to potentially reduce latency

## Step 5: Peak Hours & Bandwidth Usage

High network traffic — on your end or from your ISP — can cause slowdowns.

- 
Note what time of day issues occur (ISPs may throttle speeds during peak hours)
- 
Check if others on your network are streaming or gaming simultaneously
- 
Are you live-streaming the Small Cap stream at the same time? Try turning off the stream and see if performance improves
- 
If issues persist, contact your ISP — they may be able to upgrade your modem/router at no cost

#### Close Bandwidth-Heavy Applications

- 
Streaming services (Netflix, YouTube, Spotify)
- 
Cloud backup services (Dropbox, Google Drive, OneDrive)
- 
Other trading platforms or market data feeds

## Step 6: Firewall & Antivirus

Security software can sometimes interfere with platform performance.

- 
Temporarily disable antivirus software (e.g., Norton, McAfee) to test for interference
- 
To access our platform, please whitelist the following URLs in your firewall:
- 
Chatroom: https://chatroom.warriortrading.com
- 
Simulator: https://sim.warriortrading.com
Note: Both URLs must be whitelisted separately. Whitelisting warriortrading.com alone will not grant access to these features.

## Step 7: Browser & CPU Optimization

Web-based platforms require significant CPU power to process all the data passing through Level 2 and to render chart data — far more than a traditional desktop platform. Making sure your system is sufficient and that you are actively managing your computer resources is very important for a smooth experience.

#### General Browser Tips

- 
✅  Use Google Chrome or Mozilla Firefox — Safari is not supported
- 
✅  Open an Incognito / Private Window to test without extensions
- 
✅  Disable browser extensions temporarily (especially ad blockers and VPNs)
- 
✅  Clear your browser cache and cookies
- 
✅  Avoid excessive widgets or pop-out widget windows

#### Monitor CPU Usage with the Browser Task Manager

To help us further troubleshoot your performance issues, use the built-in Browser Task Manager to identify which tabs or processes are consuming the most CPU.
Note that browser task managers report CPU as a percentage of a single core, not your total CPU capacity.  Also a browser tab/window normally takes up one CPU core. So the more pop-ups you have, the more cores you will take up on your computer. This means a reading of 90%+ indicates, for one browser tab, Chrome is nearly maxing out one CPU core even if your overall system CPU looks fine in Windows Task Manager.
This tab also can't access your other cores to spread the load, so it becomes a bottleneck, causing browser lag, delayed updates, or unresponsiveness for that particular tab. 
When Chrome's usage consistently pushes near or above 100% on a single core, you may experience:

- 
Browser stuttering or freezing
- 
Delayed data updates
- 
Sluggish platform responsiveness

##### How to Open the Browser Task Manager

Google Chrome:

- 
Click the three-dot menu (⋮) in the top-right corner
- 
Hover over More Tools
- 
Select Task Manager
Mozilla Firefox:

- Type about:performance in the address bar and press Enter

##### What to Do Once It's Open

- 
Select all tasks and click the CPU column header to sort by CPU load (highest to lowest)
- 
Screen record or actively monitor the Task Manager throughout your trading session
- 
Take note if any tab or process exceeds 90% CPU usage at any point
- 
Slowly close tabs and widgets one at a time until CPU usage stays consistently below 100%
Tip: Start by closing charts in the DTD platform first, as these are among the most CPU-intensive elements.

- 
You can also reduce chart load by updating your Market Data Refresh Rate to 1 second:
[How to Update Market Data Refresh Rate](https://support.warriortrading.com/support/solutions/articles/19000108691-issues-with-live-stream-or-day-trade-dash-wt#How-to-Update-Market-Data-Refresh-Rate)

## Step 8: General System Maintenance

Basic computer hygiene can go a long way.

- 
Close unused tabs and applications to free up memory
- 
Connect to a charger if you're on a laptop to ensure full performance mode is available
- 
Restart your computer if it has been running for multiple days without a reboot

## Quick Checklist Summary

| 
Step | 
Action
| 
✅ | 
Sync your system clock (Windows or Mac)
| 
✅ | 
Set Power Mode to Best Performance (plugged in)
| 
✅ | 
Switch to a wired Ethernet connection
| 
✅ | 
Run a speed test at speedtest.net
| 
✅ | 
Reset your router/modem
| 
✅ | 
Disconnect VPN (or try NordVPN via New York)
| 
✅ | 
Close streaming/cloud/backup apps
| 
✅ | 
Disable antivirus/extensions temporarily
| 
✅ | 
Open Browser Task Manager and monitor CPU usage
| 
✅ | 
Close charts and reduce widget count
| 
✅ | 
Use Chrome or Firefox, clear cache
| 
✅ | 
Restart your computer

## Still experiencing issues?

If none of the above steps resolve your latency, please submit a support ticket here: https://warrior.app/contact and include the following:

- Your network speed test results.
- Your browser and operating system.
- Your hardware information (processor, RAM, and graphics card): https://support.warriortrading.com/support/solutions/articles/19000097233-check-computer-specifications
- A phone video, camera video, or screen recording of both your Browser's Task Manager and Computer Task Manager/Activity Monitor (Mac) as directed in Step 7.
- The time of day the issues typically occur.
