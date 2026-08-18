<!-- source: https://support.warriortrading.com/support/solutions/articles/19000113122-how-to-open-ports-in-windows-10-and-windows-11-firewall -->
<!-- category: General Tech Support -->
<!-- folder: General Tech How-Tos -->
<!-- modified: Tue, Dec 5, 2023 at 1:50 PM -->

# How to Open Ports in Windows 10 and Windows 11 Firewall

Firewall and security settings are often responsible for a website or component of a website not working as intended. Something that often help resolve that issue is to open ports within that firewall or security settings to allow those components through without interference.

Adjustments to firewall settings tend to be most realistic on a home network. Employer networks (or school networks and other public networks) tend to have extremely strict network settings, so getting an administrator to lower security thresholds might be a long shot. However, if you have a good relationship with your IT department, it may be worth checking into. 

Here's how to open ports in Windows 10/11 firewall:

1. Open Windows Defender Firewall on your computer.

[image]

2. Click on Advanced settings.

[image]

3. Go to Inbound Rules.
4. Select to create a New Rule.

[image]

5. Select Port.
6. Click Next.

[image]

7. Select either TCP or UDP. For the Warrior Trading's services, these settings will have to be applied to both TCP or UDP. (Select one this time around, and then come back to this step and select the other).

8. Enter the specific local ports to apply these settings to.

- For the WT live trading rooms, enter these ports: 80, 443, 1935, 8180, 8181
- For the WT Sim, enter these ports: 9997, 9999, 27, 28, 29

9. Click Next.

[image]

10. Click to Allow the connection
11. Click Next.

[image]

12. Apply the rule to all options by checking the box for: Domain, Private, Public.
13. Click Next.

[image]

14. Enter a Name and Description of your choice to help identify the rule that you've created.
15. Click Finish.

16. For the Warrior Trading live trading rooms, you'll now want to go back and repeat the steps, choosing the other option for TCP / UDP (step 7) that you didn't choose the first time around.

[image]

Still have questions? Please [reach out to our Support Team](http://support.warriortrading.com/support/tickets/new), and we'd be happy to help.
