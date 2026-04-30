# Gamma Vacuum DIGITEL SPCe
This project demonstrates how to read data from DIGITEL SPCe controller via Serial port. Python script read pressure values and save it to csv file. If you want to monitor pressure leakage you can load csv and create graph with pyqtgraph.  
desktop_monitor.py works as live pressure monitor  
SPCe type: https://www.gammavacuum.com/products/digitel-controllers/3337/digitel-spc  
Command packet structure used from SPCe manual  
Python version: 3.12.7  

Used components:
- DIGITEL SPCe controller
- UGREEN USB 2.0 to RS-232 COM Port DB9 (M) Adapter Cable Black 1.5m
- The null modem serial cable

# PyQt Graph:
<img width="1193" height="720" alt="Screenshot 2026-04-28 at 18 28 24" src="https://github.com/user-attachments/assets/92757b4b-33fb-41a3-a8a7-38af814f838d" />
