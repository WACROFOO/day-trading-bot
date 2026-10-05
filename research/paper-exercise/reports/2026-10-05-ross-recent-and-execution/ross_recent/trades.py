"""Ross Cameron June-July 2026 trades, transcribed from the extraction JSON the
workflow handed over (his own words; video id + timestamp per row).

Columns: vid, ts, session_date, raw_ticker, sym_candidates, acct, outcome,
entry_price, tspec, entry_time_text, exit_price, shares, pnl_usd, setup, confidence

tspec (my reading of entry_time_text, nothing else):
  "=HH:MM"  stated clock time       "~HH:MM"  stated approximately ("just before the bell" = 09:29, "at the open" = 09:30)
  ">HH:MM"  not before               "<HH:MM"  not after (exclusive)
  combined e.g. ">07:00<09:30";  ""  nothing usable
  "pre-market" text -> "<09:30"; "after the open" -> ">09:30"; "afternoon" -> ">12:00"
sym_candidates: [] when no ticker is named; several when the transcript is ambiguous (first with bars wins).
"""
N = None
T = [
# ---- 2026-06-01 eMRYIeDWZkQ
("eMRYIeDWZkQ", "00:11:06", "2026-06-01", "MTEK? (spoken MTech/Mitek)", ["MTEK"], "?", "win", 1.70, "", "", N, N, 3500, "first pop on space/AI headline", "medium"),
("eMRYIeDWZkQ", "00:12:51", "2026-06-01", "HKIT", ["HKIT"], "?", "loss", N, "", "", N, N, -3100, "micro pullback under VWAP 10s", "high"),
("eMRYIeDWZkQ", "00:13:46", "2026-06-01", "MASK? (as transcribed)", ["MASK"], "?", "win", 5.50, "", "", N, N, 4000, "break of 5.50 after descending resistance", "high"),
# ---- 2026-06-10 ltdLO7sAzow
("ltdLO7sAzow", "00:07:42", "2026-06-10", "DSY", ["DSY"], "small", "win", 3.10, ">07:42<09:30", "after 07:42 (scanner alert), pre-market", N, N, 1014.69, "micro pullback 10s, first pullback", "high"),
("ltdLO7sAzow", "00:04:42", "2026-06-10", "VSME", ["VSME"], "main", "not stated", N, "", "", N, N, N, "not stated", "medium"),
# ---- 2026-06-15 KlIE5mjS2dM
("KlIE5mjS2dM", "00:02:33", "2026-06-15", "JRSH", ["JRSH"], "?", "win", N, "=08:25", "08:25", N, N, 21000, "pullback, first 1-min candle new high", "high"),
("KlIE5mjS2dM", "00:07:03", "2026-06-15", "CUPR", ["CUPR"], "?", "win", N, ">09:00", "after 09:00", N, N, N, "buying the pullbacks (aggregate)", "medium"),
("KlIE5mjS2dM", "00:06:37", "2026-06-12", "CUPR", ["CUPR"], "?", "win", N, "", "", N, N, 26000, "not stated", "medium"),
# ---- 2026-06-18 Zf2p9c1qHjg
("Zf2p9c1qHjg", "00:04:38", "2026-06-18", "CDTI", ["CDTI"], "small", "scratch", 1.39, "", "", 1.40, 5000, 62.37, "micro pullback", "high"),
("Zf2p9c1qHjg", "00:05:11", "2026-06-18", "CDTI", ["CDTI"], "small", "loss", 2.00, "", "", N, N, N, "first 1-min candle new high after 1-min pullback", "high"),
("Zf2p9c1qHjg", "00:06:08", "2026-06-18", "CDTI", ["CDTI"], "small", "loss", N, "", "", N, N, N, "pullback to ascending support (revenge)", "high"),
("Zf2p9c1qHjg", "00:06:45", "2026-06-18", "WOK", ["WOK"], "small", "win", N, "", "", N, N, 586.60, "micro pullback (reverse split day)", "high"),
# ---- 2026-06-23 10ogBWqgprI
("10ogBWqgprI", "00:04:52", "2026-06-23", "ICCM", ["ICCM"], "small", "win", 6.99, "", "", 8.03, N, 614.47, "micro pullback under 7 on breaking news", "high"),
# ---- 2026-06-25 P5Sn_mWJdy0
("P5Sn_mWJdy0", "00:08:40", "2026-06-25", "MIMI", ["MIMI"], "main", "not stated", N, "", "", N, N, N, "first spike on news", "medium"),
("P5Sn_mWJdy0", "00:09:30", "2026-06-25", "MIMI", ["MIMI"], "small", "win", N, ">08:26", "after ~08:26 (scanner alert)", N, N, 300, "break of VWAP 10s, MACD positive", "high"),
("P5Sn_mWJdy0", "00:09:47", "2026-06-25", "MIMI", ["MIMI"], "small", "win", N, "", "", N, N, N, "VWAP second cross, inverted H&S", "medium"),
("P5Sn_mWJdy0", "00:09:52", "2026-06-25", "MIMI", ["MIMI"], "small", "win", N, "", "", N, N, N, "HOD breakout (squeeze through 5)", "medium"),
("P5Sn_mWJdy0", "00:10:22", "2026-06-25", "FCUV", ["FCUV"], "small", "win", N, "", "", N, N, 341, "break of VWAP after curl", "high"),
# ---- 2026-06-29 rhOjs_8rh6w
("rhOjs_8rh6w", "00:02:24", "2026-06-29", "UPC", ["UPC"], "main", "win", N, "", "", N, N, N, "curl after base", "medium"),
("rhOjs_8rh6w", "00:02:36", "2026-06-29", "UPC", ["UPC"], "small", "win", N, "", "", N, N, N, "same UPC move", "medium"),
("rhOjs_8rh6w", "00:03:24", "2026-06-29", "UPC", ["UPC"], "main", "loss", N, "", "", N, N, N, "breakouts on curl after drop (3 aggregated)", "medium"),
("rhOjs_8rh6w", "00:00:03", "2026-06-29", "UNKNOWN", [], "?", "not stated", N, "", "", N, N, N, "not stated", "low"),
# ---- 2026-07-01 iZ-mXl0ga3U
("iZ-mXl0ga3U", "00:01:44", "2026-07-01", "TC", ["TC"], "margin", "loss", N, "=07:00", "07:00", N, N, -394, "dip buy for curl", "high"),
("iZ-mXl0ga3U", "00:03:16", "2026-07-01", "CF", ["CF"], "?", "win", N, "=07:06", "07:06", N, N, 7300, "break through descending resistance", "high"),
("iZ-mXl0ga3U", "00:04:07", "2026-07-01", "CF", ["CF"], "?", "scratch", N, "~09:29", "just before 09:30", N, N, N, "break of VWAP", "high"),
("iZ-mXl0ga3U", "00:04:34", "2026-07-01", "GEM", ["GEM"], "?", "loss", 10.00, "<09:30", "pre-market", N, N, N, "break of 10 pre-market", "high"),
("iZ-mXl0ga3U", "00:04:59", "2026-07-01", "DXST", ["DXST"], "?", "not stated", N, "", "", N, N, N, "micro pullback / curl for squeeze through 4", "medium"),
("iZ-mXl0ga3U", "00:00:14", "2026-07-01", "UNKNOWN (small 1)", [], "small", "win", N, "", "", N, N, N, "not stated", "low"),
("iZ-mXl0ga3U", "00:00:14b", "2026-07-01", "UNKNOWN (small 2)", [], "small", "win", N, "", "", N, N, N, "not stated", "low"),
# ---- 2026-07-06 4T2x29K1TDk
("4T2x29K1TDk", "00:06:10", "2026-07-06", "LHSW", ["LHSW"], "?", "win", N, "", "", N, N, 9157.59, "break of level after holding support", "high"),
("4T2x29K1TDk", "00:04:15", "2026-07-06", "GMEX", ["GMEX"], "?", "loss", N, ">08:30", "after 08:30 (scanner alert)", N, N, N, "news squeeze, curl back over VWAP", "high"),
# ---- 2026-07-09 49ykxodJcFc (VRX = VRAX, named so in miyJZq-5uIg same day)
("49ykxodJcFc", "00:03:39", "2026-07-09", "VRX", ["VRAX", "VRX"], "small", "win", N, ">07:30", "after 07:30", N, N, N, "pullback then pop", "medium"),
("49ykxodJcFc", "00:03:51", "2026-07-09", "VRX", ["VRAX", "VRX"], "main", "win", 6.55, "", "", N, N, 19000, "break through 6.55", "high"),
("49ykxodJcFc", "00:04:11", "2026-07-09", "VRX", ["VRAX", "VRX"], "main", "loss", N, "", "", N, N, N, "pop after pullback", "medium"),
("49ykxodJcFc", "00:04:22", "2026-07-09", "VRX", ["VRAX", "VRX"], "main", "loss", 8.00, "", "", N, N, N, "break through 8 (PM high)", "medium"),
("49ykxodJcFc", "00:04:53", "2026-07-09", "VRX", ["VRAX", "VRX"], "main", "not stated", N, "", "", N, N, N, "not stated", "low"),
("49ykxodJcFc", "00:05:07", "2026-07-09", "VRX", ["VRAX", "VRX"], "main", "win", 10.00, "", "", N, N, N, "break through 10, adds 10.50/11", "medium"),
("49ykxodJcFc", "00:05:40", "2026-07-09", "VRX", ["VRAX", "VRX"], "main", "loss", 12.00, "", "", 11.30, N, N, "break of 12", "medium"),
# ---- 2026-07-13 RZbM0qXOFbc
("RZbM0qXOFbc", "00:05:09", "2026-07-13", "PLSM", ["PLSM"], "small", "win", 6.52, "", "", 7.70, 2000, 2300, "dip after squeeze 5 -> 6.50", "high"),
("RZbM0qXOFbc", "00:06:59", "2026-07-13", "PLSM", ["PLSM"], "main", "loss", 9.30, "", "", N, 30000, -26000, "re-break of 9.59 backside (FOMO)", "high"),
("RZbM0qXOFbc", "00:07:08", "2026-07-13", "PLSM", ["PLSM"], "small", "loss", 9.57, "", "", 8.00, N, N, "break of 9.50", "high"),
("RZbM0qXOFbc", "00:08:39", "2026-07-13", "VE/VEEE", ["VEEE", "VE"], "main", "win", N, "", "", N, N, 6000, "curl back through 7", "high"),
("RZbM0qXOFbc", "00:08:51", "2026-07-13", "VE/VEEE", ["VEEE", "VE"], "main", "win", N, "", "", N, N, N, "break of VWAP", "high"),
("RZbM0qXOFbc", "00:09:00", "2026-07-13", "VE/VEEE", ["VEEE", "VE"], "main", "win", N, "", "", N, N, N, "re-entry on squeeze, add", "medium"),
("RZbM0qXOFbc", "00:09:08", "2026-07-13", "VE/VEEE", ["VEEE", "VE"], "main", "not stated", N, "", "", N, N, N, "dip buy after consolidation", "low"),
("RZbM0qXOFbc", "00:09:17", "2026-07-13", "VE/VEEE", ["VEEE", "VE"], "main", "loss", N, "", "", N, N, N, "not stated (2 losses)", "medium"),
("RZbM0qXOFbc", "00:09:30", "2026-07-13", "VE/VEEE", ["VEEE", "VE"], "main", "win", N, "<09:30", "before 09:30", N, N, N, "rally into open above VWAP, micro pullback", "medium"),
("RZbM0qXOFbc", "00:09:41", "2026-07-13", "VE/VEEE", ["VEEE", "VE"], "main", "win", 12.00, "=09:30", "09:30 (at the open)", 13.00, N, N, "dip buy off 12 at the open", "high"),
("RZbM0qXOFbc", "00:08:28", "2026-07-13", "VE/VEEE", ["VEEE", "VE"], "small", "win", N, "", "", N, N, N, "not stated", "low"),
# ---- 2026-07-14/15 TzpOIMOrU7I
("TzpOIMOrU7I", "00:00:26", "2026-07-14", "UNKNOWN A", [], "?", "win", N, "", "", N, N, N, "not stated", "low"),
("TzpOIMOrU7I", "00:00:32", "2026-07-14", "UNKNOWN", [], "?", "loss", N, "", "", N, N, N, "not stated", "low"),
("TzpOIMOrU7I", "00:00:32b", "2026-07-14", "UNKNOWN", [], "?", "win", N, "", "", N, N, N, "not stated", "low"),
("TzpOIMOrU7I", "00:00:37", "2026-07-14", "UNKNOWN B", [], "?", "loss", N, "", "", N, N, -6000, "not stated", "medium"),
("TzpOIMOrU7I", "00:01:24", "2026-07-15", "ERNA", ["ERNA"], "small", "not stated", N, ">07:35", "after ~07:35-07:50", N, N, N, "early pop", "medium"),
("TzpOIMOrU7I", "00:04:01", "2026-07-15", "VIVS", ["VIVS"], "main", "win", 1.80, "", "", 2.90, N, N, "break of 1.80 (200 MA), add 2.50", "high"),
("TzpOIMOrU7I", "00:04:10", "2026-07-15", "VIVS", ["VIVS"], "main", "scratch", 3.00, "", "", N, N, N, "break over 3", "high"),
("TzpOIMOrU7I", "00:04:25", "2026-07-15", "VIVS", ["VIVS"], "small", "loss", 3.00, "", "", N, N, N, "break over 3", "high"),
("otCqRWCJ2uA", "00:01:22", "2026-07-16", "UNKNOWN", [], "small", "win", N, "", "", N, N, 500, "not stated (day total)", "low"),
# ---- 2026-07-22 -QZ8buLplck
("-QZ8buLplck", "00:06:21", "2026-07-22", "LABT", ["LABT"], "small", "win", N, "", "", N, N, 1800, "micro pullback after squeeze to 3.60", "high"),
("-QZ8buLplck", "00:06:46", "2026-07-22", "LABT", ["LABT"], "small", "win", 5.65, "", "", N, N, 400, "pullback re-entry (filled higher)", "high"),
# ---- 2026-07-24 b-iczURZwJY
("b-iczURZwJY", "00:03:20", "2026-07-24", "EXYN", ["EXYN"], "small", "win", N, "", "", N, N, 766.56, "HOD breakout", "high"),
("b-iczURZwJY", "00:04:37", "2026-07-24", "MSS", ["MSS"], "small", "loss", 4.25, "", "", N, 2000, -716.45, "curl over VWAP", "high"),
# ---- 2026-07-27 83Yuliq1vHA
("83Yuliq1vHA", "00:05:48", "2026-07-27", "VTIX", ["VTIX"], "small", "win", 3.50, ">09:15", "after ~09:15-09:17 (scanner alert)", N, 4000, 4000, "pullback, break through 3.70", "high"),
("83Yuliq1vHA", "00:04:43", "2026-07-27", "EDBL", ["EDBL"], "main", "not stated", N, "", "", N, N, N, "not stated", "medium"),
# ---- 2026-06-02 hQCwquA6O7E
("hQCwquA6O7E", "00:08:43", "2026-06-02", "BJDX", ["BJDX"], "?", "win", 6.80, "~07:19", "~07:19 (entry vs exit not distinguished)", N, N, 1723.23, "starter on dip to ascending support 10s", "high"),
# ---- 2026-06-08/09 znf0QIW8KRE
("znf0QIW8KRE", "00:07:16", "2026-06-08", "NPT", ["NPT"], "?", "not stated", N, "", "", N, N, N, "not stated", "low"),
("znf0QIW8KRE", "00:15:46", "2026-06-09", "AZI", ["AZI"], "small", "win", 4.98, "", "", 6.82, N, 816, "micro pullback dip buy 1-min", "medium"),
("znf0QIW8KRE", "00:10:08", "2026-06-09", "D AIC (possibly AZI)", [], "main", "win", N, "", "", N, N, 11000, "not stated", "low"),
("znf0QIW8KRE", "00:10:08b", "2026-06-09", "UNKNOWN", [], "main", "loss", N, "", "", N, N, -8000, "not stated", "low"),
("znf0QIW8KRE", "00:10:08c", "2026-06-09", "UNKNOWN", [], "main", "win", N, "", "", N, N, 23000, "not stated", "low"),
("znf0QIW8KRE", "00:10:08d", "2026-06-09", "UNKNOWN", [], "main", "win", N, "", "", N, N, 15000, "not stated", "low"),
("znf0QIW8KRE", "00:10:01", "2026-06-09", "CCTG", ["CCTG"], "main", "loss", N, "", "", N, N, -27000, "higher-risk trade with cushion", "high"),
# ---- 2026-06-10/11 vcfpJWEqaTU
("vcfpJWEqaTU", "00:07:15", "2026-06-10", "DSY", ["DSY"], "main", "win", N, "<09:30", "pre-market", N, N, 120000, "not stated (aggregate)", "medium"),
("vcfpJWEqaTU", "00:07:15b", "2026-06-10", "DSY", ["DSY"], "main", "win", N, ">09:30", "after the 09:30 open", N, N, 20000, "not stated", "medium"),
("vcfpJWEqaTU", "00:01:46", "2026-06-11", "FGL", ["FGL"], "main", "loss", N, "", "", N, 35000, -17291.27, "second pullback", "high"),
("vcfpJWEqaTU", "00:09:02", "2026-06-11", "EDHL", ["EDHL"], "main", "win", 5.65, "<09:30", "pre-market", N, 20000, 30000, "squeeze after bottoming-tail dip, scale in", "medium"),
("vcfpJWEqaTU", "00:09:59", "2026-06-11", "EDHL", ["EDHL"], "main", "win", 8.40, "<09:30", "pre-market", 9.00, N, N, "micro pullback / break HOD after VWAP reclaim", "medium"),
("vcfpJWEqaTU", "00:11:06", "2026-06-11", "EDHL", ["EDHL"], "main", "not stated", N, "=08:57", "last trade 08:57 (aggregate)", N, N, N, "continuation entries (aggregate)", "low"),
("vcfpJWEqaTU", "00:08:01", "2026-06-11", "EDHL", ["EDHL"], "small", "not stated", N, "<09:30", "pre-market", N, N, N, "pullback", "medium"),
("vcfpJWEqaTU", "00:12:15", "2026-06-11", "QH", ["QH"], "main", "win", N, "", "", N, N, N, "not stated", "medium"),
# ---- SpaceX IPO, symbol never stated
("ZVM1OzsCRcc", "00:01:34", "2026-06-12", "SpaceX IPO (symbol not stated)", [], "?", "not stated", 135.0, "", "", N, N, N, "IPO allocation", "medium"),
("oRX-scXUU0U", "00:00:39", "2026-06-12", "SpaceX IPO (symbol not stated)", [], "?", "win", N, "", "", N, N, 40000, "IPO-day trading", "medium"),
# ---- 2026-06-16 ZVM1OzsCRcc
("ZVM1OzsCRcc", "00:00:15", "2026-06-16", "OPTX", ["OPTX"], "main", "loss", N, "", "", N, 20000, -4300, "breaking news, bought immediately", "high"),
("ZVM1OzsCRcc", "00:02:22", "2026-06-16", "TDIC", ["TDIC"], "main", "win", N, "", "", N, N, 2000, "curl back up below VWAP", "high"),
("ZVM1OzsCRcc", "00:02:36", "2026-06-16", "TDIC", ["TDIC"], "main", "loss", N, "", "", N, 20000, -15000, "1-min micro pullback over 11.50", "high"),
("ZVM1OzsCRcc", "00:06:20", "2026-06-16", "UNKNOWN", [], "small", "win", N, "", "", N, N, N, "not stated", "medium"),
# ---- 2026-06-18 (Friday mapped to Thursday) oRX-scXUU0U
("oRX-scXUU0U", "00:08:07", "2026-06-18", "UNKNOWN IPO", [], "?", "not stated", N, "", "", N, N, N, "small-cap IPO", "low"),
("oRX-scXUU0U", "00:13:15", "2026-06-18", "WOK", ["WOK"], "?", "not stated", N, "", "", N, N, N, "recent reverse split", "low"),
("oRX-scXUU0U", "00:03:29", "2026-06-18", "UNKNOWN", [], "small", "loss", N, "", "", N, N, N, "not stated", "low"),
# ---- 2026-06-23/24 tfTdAbm9oTI
("tfTdAbm9oTI", "00:00:43", "2026-06-23", "UNKNOWN", [], "main", "loss", N, "<09:30", "before the 09:30 open", N, N, -8000, "not stated", "medium"),
("tfTdAbm9oTI", "00:00:43b", "2026-06-23", "FCUV", ["FCUV"], "main", "loss", N, ">09:30", "after the 09:30 open", N, N, -28000, "post-open, stubborn", "medium"),
("tfTdAbm9oTI", "00:04:34", "2026-06-24", "PLSM", ["PLSM"], "main", "win", N, "", "pre-market (says 10:07, inconsistent)", N, N, 8921.72, "blue sky, in and out (aggregate)", "high"),
("tfTdAbm9oTI", "00:05:52", "2026-06-24", "FRTT", ["FRTT"], "main", "win", N, "", "", N, N, 500, "blue sky over 4, mid-move", "high"),
# ---- 2026-06-25/26 hUb-n3kzqjI
("hUb-n3kzqjI", "00:00:46", "2026-06-25", "UNKNOWN (SpaceX catalyst)", [], "main", "win", N, "", "~09:00-09:15", N, N, N, "breaking news", "low"),
("hUb-n3kzqjI", "00:02:09", "2026-06-26", "ZDAI", ["ZDAI"], "small", "win", N, "", "", N, N, 1000, "second pullback 10s", "medium"),
("hUb-n3kzqjI", "00:02:44", "2026-06-26", "ZDAI", ["ZDAI"], "main", "loss", 4.45, "", "", N, N, -25000, "pullback after 4.70 high, big size (FOMO)", "high"),
("hUb-n3kzqjI", "00:07:45", "2026-06-26", "SHPH", ["SHPH"], "main", "loss", N, "", "", N, N, -3000, "none (dogecoin headline)", "high"),
("hUb-n3kzqjI", "00:09:22", "2026-06-26", "S. (S-dot)", ["SDOT"], "main", "win", 10.00, "<09:30", "before the 09:30 open", N, N, 5800, "break of 10 over VWAP", "high"),
# ---- 2026-06-29 tQ7cYcI2tNk
("tQ7cYcI2tNk", "00:08:00", "2026-06-29", "UPC", ["UPC"], "small", "win", 9.85, "", "", 13.00, N, 3400, "curl back to VWAP, false breakout then rip", "high"),
("tQ7cYcI2tNk", "00:09:16", "2026-06-29", "UPC", ["UPC"], "small", "loss", N, "", "", N, N, N, "re-entry on pullback, chased", "high"),
# ---- 2026-07-02 3dXvK41dpd4
("3dXvK41dpd4", "00:03:27", "2026-07-02", "CX", ["CX"], "?", "win", N, "", "", N, N, N, "micro pullback after tapping 5", "medium"),
("3dXvK41dpd4", "00:03:40", "2026-07-02", "CX", ["CX"], "?", "loss", 5.76, "", "", N, 20000, N, "add back on the way up", "medium"),
("3dXvK41dpd4", "00:04:00", "2026-07-02", "CX", ["CX"], "?", "win", N, "", "", N, N, N, "dip buy", "medium"),
# ---- 2026-07-07 Dpba4GF0KhY
("Dpba4GF0KhY", "00:02:12", "2026-07-07", "CLRO", ["CLRO"], "main", "loss", N, "<09:30", "pre-market", N, N, -1600, "entry as it popped", "high"),
("Dpba4GF0KhY", "00:02:54", "2026-07-07", "CLRO", ["CLRO"], "small", "not stated", N, "<09:30", "pre-market", N, N, N, "not stated", "medium"),
("Dpba4GF0KhY", "00:03:33", "2026-07-07", "CLRO", ["CLRO"], "main", "loss", N, "~09:07", "~09:07 or just before", N, N, N, "break HOD after VWAP reclaim", "high"),
("Dpba4GF0KhY", "00:04:11", "2026-07-07", "CLRO", ["CLRO"], "main", "win", 9.40, ">09:07<09:30", "after 09:07, before 09:30", 10.00, N, N, "anticipated flat-top break", "high"),
# ---- 2026-07-09 miyJZq-5uIg
("miyJZq-5uIg", "00:03:37", "2026-07-09", "VRAX", ["VRAX", "VRX"], "small", "win", 6.30, "<09:30", "pre-market", N, N, 2262.35, "second micro pullback, break of 6", "high"),
("miyJZq-5uIg", "00:04:39", "2026-07-09", "VRAX", ["VRAX", "VRX"], "main", "not stated", N, "", "", N, N, N, "micro pullback at 6", "low"),
# ---- 2026-07-13 S2sOq-stPgA
("S2sOq-stPgA", "00:04:20", "2026-07-13", "PLSM", ["PLSM"], "small", "win", N, ">07:58", "shortly after ~07:58", N, 2000, 2363.44, "dip buy after first leg", "high"),
("S2sOq-stPgA", "00:05:15", "2026-07-13", "PLSM", ["PLSM"], "small", "loss", 9.50, "", "", N, N, N, "backside curl for 9.59", "high"),
("S2sOq-stPgA", "00:05:15b", "2026-07-13", "PLSM", ["PLSM"], "main", "loss", 9.50, "", "", N, N, N, "backside curl for 9.59 (FOMO)", "high"),
("S2sOq-stPgA", "00:07:51", "2026-07-13", "VEEE", ["VEEE", "VE"], "main", "win", N, "", "", N, N, N, "breaking news, as it pulled away", "medium"),
("S2sOq-stPgA", "00:07:57", "2026-07-13", "VEEE", ["VEEE", "VE"], "small", "win", 11.00, "", "", N, 1000, 765, "pullback around 11", "high"),
# ---- 2026-07-14/15 8IYunlNOVmM
("8IYunlNOVmM", "00:05:03", "2026-07-14", "UBXG", ["UBXG"], "main", "loss", N, "", "", N, N, -6000, "pullback, repeated re-entries", "medium"),
("8IYunlNOVmM", "00:05:35", "2026-07-15", "ERNA", ["ERNA"], "small", "win", 9.37, "", "", N, 4000, 873.52, "starter on dip, add for break of 10", "high"),
("8IYunlNOVmM", "00:07:30", "2026-07-15", "VIVS", ["VIVS"], "small", "win", 1.91, "", "", N, 4000, N, "break of 2 after 200 MA at 1.80", "high"),
("8IYunlNOVmM", "00:07:54", "2026-07-15", "VIVS", ["VIVS"], "small", "loss", N, "", "", N, 2000, N, "add back on dip", "high"),
# ---- 2026-07-20 mDQEtmG0PCw
("mDQEtmG0PCw", "00:02:31", "2026-07-20", "BIYA", ["BIYA"], "main", "win", 7.50, ">07:00<09:30", "pre-market, after 07:00", N, N, N, "break of resistance after retest and curl", "high"),
("mDQEtmG0PCw", "00:05:33", "2026-07-20", "BIYA", ["BIYA"], "main", "loss", N, "", "", N, N, N, "add that raised cost basis", "medium"),
("mDQEtmG0PCw", "00:05:45", "2026-07-20", "BIYA", ["BIYA"], "main", "loss", N, "", "", N, N, N, "dip buy for curl (2 attempts)", "medium"),
# ---- 2026-07-24 CA8i4Rc2bUY
("CA8i4Rc2bUY", "00:04:01", "2026-07-24", "GEM/GM", ["GEM"], "main", "scratch", N, "=07:00", "07:00", N, 10000, 579, "squeeze at 07:00, in a little high", "high"),
("CA8i4Rc2bUY", "00:02:59", "2026-07-24", "ZCMD", ["ZCMD"], "main", "loss", 5.50, "", "", N, N, -11000, "pullback after spike, break over 6", "high"),
("CA8i4Rc2bUY", "00:03:28", "2026-07-24", "ZCMD", ["ZCMD"], "main", "loss", N, "", "", N, N, -1000, "curl back up re-entry", "high"),
("CA8i4Rc2bUY", "00:05:20", "2026-07-24", "EHGO", ["EHGO"], "main", "win", 3.00, "<09:30", "before 09:30", N, 35000, 41000, "break of 3 on first 5-min candle new high", "high"),
# ---- 2026-07-28 1ml6zHikpsE
("1ml6zHikpsE", "00:04:44", "2026-07-28", "INLF", ["INLF"], "main", "loss", 7.80, ">09:30", "after the 09:30 open", N, 25000, -32000, "halt-resumption dip, break through 8.20", "high"),
("1ml6zHikpsE", "00:06:54", "2026-07-28", "UNKNOWN", [], "small", "loss", N, "", "", N, N, -7000, "not stated", "medium"),
# ---- 2026-06-04 A7acrZyX9VU
("A7acrZyX9VU", "00:04:23", "2026-06-04", "STI", ["STI"], "main", "win", N, ">07:00<07:16", "07:00-07:15 (aggregate)", N, N, N, "breaking the ice (aggregate)", "low"),
("A7acrZyX9VU", "00:04:47", "2026-06-04", "STI", ["STI"], "main", "win", 17.70, "=08:35", "08:35", N, N, 59000, "break of PM high 17.70", "high"),
("A7acrZyX9VU", "00:05:06", "2026-06-04", "STI", ["STI"], "main", "win", N, "", "", N, N, N, "pullback after 17.70 breakout", "medium"),
("A7acrZyX9VU", "00:05:18", "2026-06-04", "STI", ["STI"], "main", "loss", 26.00, "", "", N, N, -12000, "break of 26", "high"),
# ---- 2026-06-08..11 5UBYoh6J2e0
("5UBYoh6J2e0", "00:00:08", "2026-06-08", "UNKNOWN", [], "small", "win", N, "", "", N, N, 416, "not stated", "low"),
("5UBYoh6J2e0", "00:00:27", "2026-06-09", "UNKNOWN", [], "small", "win", N, "", "", N, N, 800, "not stated", "low"),
("5UBYoh6J2e0", "00:00:34", "2026-06-10", "UNKNOWN", [], "small", "win", N, "", "", N, N, 1100, "not stated", "low"),
("5UBYoh6J2e0", "00:08:19", "2026-06-11", "EDHL", ["EDHL"], "small", "win", 6.83, "", "", 8.14, N, 782.55, "dip buy / micro pullback", "high"),
("5UBYoh6J2e0", "00:09:31", "2026-06-11", "FGL", ["FGL"], "small", "win", 3.45, "", "", 3.84, N, 500, "punch for break of 3.50", "high"),
("5UBYoh6J2e0", "00:07:39", "2026-06-11", "FGL", ["FGL"], "main", "loss", N, "", "", N, N, N, "similar trade", "medium"),
("5UBYoh6J2e0", "00:10:20", "2026-06-11", "EDHL", ["EDHL"], "main", "win", N, "", "", N, N, N, "continued trading", "medium"),
("c814DtTOGDg", "00:04:26", "2026-06-16", "UPC", ["UPC"], "small", "win", 4.00, "", "", 5.84, 1289, N, "micro pullback, break back over 4", "high"),
# ---- 2026-06-22 wxcUcYbUtDw
("wxcUcYbUtDw", "00:09:49", "2026-06-22", "NXTS", ["NXTS"], "main", "win", N, ">08:22", "after 08:22", N, N, 1000, "early dip buys", "medium"),
("wxcUcYbUtDw", "00:11:14", "2026-06-22", "NXTS", ["NXTS"], "main", "win", 9.75, "", "", N, N, N, "pullback after VWAP reclaim", "medium"),
("wxcUcYbUtDw", "00:12:10", "2026-06-22", "NXTS", ["NXTS"], "main", "loss", 11.44, "<09:30", "pre-market, before 09:30", N, 9000, N, "anticipating a squeeze", "medium"),
("D8Guwf84eAA", "00:10:53", "2026-06-24", "FRTT", ["FRTT"], "small", "win", N, "", "", N, N, 1513.69, "micro pullback, buy the curl", "high"),
("D8Guwf84eAA", "00:03:58", "2026-06-24", "PLSM", ["PLSM"], "main", "not stated", N, "", "", N, N, N, "blue-sky breakout (context only)", "low"),
# ---- 2026-06-26 P5qdiBNct1c
("P5qdiBNct1c", "00:01:57", "2026-06-26", "ZDAI", ["ZDAI"], "small", "win", N, "", "", N, N, 1000, "second pullback 10s", "high"),
("P5qdiBNct1c", "00:01:33", "2026-06-26", "ZDAI", ["ZDAI"], "main", "loss", N, "", "", N, N, N, "added on squeeze, third pullback", "high"),
("P5qdiBNct1c", "00:02:52", "2026-06-26", "SDOT", ["SDOT"], "small", "win", N, "", "", N, 1000, 300, "VWAP break micro pullback", "high"),
("P5qdiBNct1c", "00:03:13", "2026-06-26", "SDOT", ["SDOT"], "small", "win", N, "", "", N, 1000, 300, "trade 2", "high"),
("P5qdiBNct1c", "00:03:17", "2026-06-26", "SDOT", ["SDOT"], "small", "win", N, "", "", N, N, N, "trade 3", "low"),
("P5qdiBNct1c", "00:03:17b", "2026-06-26", "SDOT", ["SDOT"], "small", "win", N, "", "", N, N, N, "trade 4", "low"),
("P5qdiBNct1c", "00:03:22", "2026-06-26", "SDOT", ["SDOT"], "small", "scratch", N, "", "", N, N, N, "trade 5", "high"),
("P5qdiBNct1c", "00:03:34", "2026-06-26", "SDOT", ["SDOT"], "small", "loss", N, "", "", N, N, N, "trade 6", "high"),
("P5qdiBNct1c", "00:03:45", "2026-06-26", "SDOT", ["SDOT"], "small", "loss", N, "~09:30", "~09:30 (opening bell)", N, N, N, "anticipating opening squeeze into halt", "high"),
("P5qdiBNct1c", "00:06:28", "2026-06-26", "SDOT", ["SDOT"], "main", "win", N, "", "", N, N, N, "not described", "medium"),
("P5qdiBNct1c", "00:06:40", "2026-06-26", "UNKNOWN", [], "main", "loss", N, "", "", N, N, N, "not stated", "low"),
# ---- 2026-06-30 PnuyhYGHuUY
("PnuyhYGHuUY", "00:07:33", "2026-06-30", "VWAV (spoken 'VWAP')", ["VWAV"], "main", "win", 8.00, "", "", N, N, 10000, "dip buy off 8 bouncing off VWAP", "medium"),
("PnuyhYGHuUY", "00:08:59", "2026-06-30", "SVRE", ["SVRE"], "main", "win", 6.98, "", "", N, N, 16000, "consolidation above VWAP, break of 7", "high"),
("PnuyhYGHuUY", "00:09:11", "2026-06-30", "SVRE", ["SVRE"], "small", "not stated", N, "", "", N, N, N, "micro pullback ~8", "medium"),
("PnuyhYGHuUY", "00:09:39", "2026-06-30", "SVRE", ["SVRE"], "main", "loss", 8.00, "=08:45", "08:45", N, 10000, -3000, "dip trade around 8", "medium"),
("PnuyhYGHuUY", "00:11:23", "2026-06-30", "JEM", ["JEM"], "main", "win", 3.70, ">08:50<09:01", "~08:50-09:00", 5.58, 15000, 46000, "running-up alert, punched as it moved faster", "high"),
("BZwJFPk3cBM", "00:16:50", "2026-07-02", "UNKNOWN", [], "small", "win", N, "", "", N, N, 2943.22, "aggregate", "low"),
# ---- 2026-07-07 550XNdh4y5k
("550XNdh4y5k", "00:06:58", "2026-07-07", "SILO", ["SILO"], "small", "win", 8.81, "", "", 9.03, N, 476, "pullback, punch for break of 9", "high"),
("550XNdh4y5k", "00:07:32", "2026-07-07", "CLRO", ["CLRO"], "small", "loss", 8.50, "", "", N, 36, -259, "break through 8.50", "high"),
("550XNdh4y5k", "00:09:02", "2026-07-07", "CLRO", ["CLRO"], "main", "not stated", N, "", "", N, N, N, "not described", "low"),
# ---- 2026-07-10 uTyfk4UvsUw
("uTyfk4UvsUw", "00:09:56", "2026-07-10", "GMM", ["GMM"], "main", "win", 5.40, "", "", N, N, N, "break of HOD 5.38 after holding support (curl)", "high"),
("uTyfk4UvsUw", "00:10:12", "2026-07-10", "GMM", ["GMM"], "main", "win", N, "", "", N, N, N, "re-entry on pullback", "high"),
("uTyfk4UvsUw", "00:10:18", "2026-07-10", "GMM", ["GMM"], "main", "loss", N, "", "", N, N, N, "adding back near 6.40 high", "medium"),
("uTyfk4UvsUw", "00:10:25", "2026-07-10", "GMM", ["GMM"], "main", "loss", N, "", "", N, N, N, "dip buy", "high"),
# ---- 2026-07-14 ut9nmRP3ENY
("ut9nmRP3ENY", "00:06:42", "2026-07-14", "NXTC", ["NXTC"], "main+small", "win", 8.40, "=07:15", "07:15", N, N, 19000, "break back over 8.40 on the curl", "high"),
("ut9nmRP3ENY", "00:07:26", "2026-07-14", "JTI", ["JTI"], "main", "loss", N, "", "", N, N, -235, "in and out brief pop", "medium"),
("ut9nmRP3ENY", "00:07:45", "2026-07-14", "UBXG", ["UBXG"], "main", "loss", N, "", "", N, N, -1700, "curl back up, add for HOD", "high"),
("ut9nmRP3ENY", "00:07:54", "2026-07-14", "UBXG", ["UBXG"], "main", "loss", N, "", "", N, N, N, "re-entry 1 under 11", "high"),
("ut9nmRP3ENY", "00:07:54b", "2026-07-14", "UBXG", ["UBXG"], "main", "loss", N, "", "", N, N, N, "re-entry 2 under 11", "high"),
("2UpK6vs0MVQ", "00:03:06", "2026-07-16", "RUBI (spoken 'Ruby')", ["RUBI"], "small", "win", 6.15, ">08:30", "after 08:30", N, N, 587.78, "break of 6 on headline squeeze", "high"),
("x0qg5eGF7zc", "00:04:52", "2026-07-20", "BIYA", ["BIYA"], "small+main", "win", N, "~07:41", "~07:41", N, N, 1100, "micro pullback, break HOD 10s", "high"),
("Ts7C0flv-1g", "00:03:43", "2026-07-23", "ZCMD", ["ZCMD"], "main", "loss", N, "", "", N, N, N, "entry as it came back up", "medium"),
("Ts7C0flv-1g", "00:05:37", "2026-07-23", "EHGO", ["EHGO"], "small", "win", N, "", "", N, N, 1868.92, "running-up alert, chased", "high"),
("Ts7C0flv-1g", "00:05:32", "2026-07-23", "EHGO", ["EHGO"], "main", "not stated", N, "", "", N, N, N, "same setup, earlier entry", "low"),
("Zj0DYfQilso", "00:05:21", "2026-07-28", "INLF", ["INLF"], "small", "loss", 8.00, "~10:30", "~10:30", 7.50, 4000, -1600, "FOMO entry on pullback expecting halt up", "high"),
("Zj0DYfQilso", "00:06:49", "2026-07-28", "INLF", ["INLF"], "small", "loss", 7.70, ">10:30", "(after the ~10:30 first entry)", N, 4000, N, "re-entry on curl", "high"),
("RMxnG64WuLc", "00:10:00", "2026-06-08", "NPT", ["NPT"], "small", "win", 8.29, ">12:00", "afternoon trade", N, 237, 416.13, "first pullback, candle over candle", "high"),
# ---- 2026-06-09/10 YDCycC3xVMA
("YDCycC3xVMA", "00:00:40", "2026-06-09", "UNKNOWN", [], "main", "loss", N, "", "", N, N, -27000, "not stated", "low"),
("YDCycC3xVMA", "00:01:01", "2026-06-09", "UNKNOWN", [], "main", "win", N, "", "", N, N, 20000, "not stated", "low"),
("YDCycC3xVMA", "00:10:51", "2026-06-10", "VSME", ["VSME"], "main", "win", N, "", "", N, N, 27000, "curl back up, first pullback", "medium"),
("YDCycC3xVMA", "00:11:15", "2026-06-10", "VSME", ["VSME"], "main", "win", N, "", "", N, N, N, "base breakout after pullback", "medium"),
("YDCycC3xVMA", "00:13:23", "2026-06-10", "GCDT", ["GCDT"], "main", "win", 2.50, "", "", N, N, 10000, "break of 2.50", "high"),
("YDCycC3xVMA", "00:17:15", "2026-06-10", "KIDZ", ["KIDZ"], "main", "not stated", N, "", "", N, N, N, "micro pullback", "medium"),
("YDCycC3xVMA", "00:16:20", "2026-06-10", "DSY", ["DSY"], "main", "win", N, "", "", N, N, 50000, "pullback 10s", "medium"),
("YDCycC3xVMA", "00:19:48", "2026-06-10", "DSY", ["DSY"], "main", "not stated", N, "", "", N, N, N, "VWAP reclaim, inverted H&S", "medium"),
("YDCycC3xVMA", "00:20:06", "2026-06-10", "DSY", ["DSY"], "main", "win", N, "", "", N, N, N, "re-entry for squeeze back to 11", "medium"),
("YDCycC3xVMA", "00:20:57", "2026-06-10", "DSY", ["DSY"], "main", "win", N, "", "", N, N, N, "halt resumption dip buy", "high"),
("YDCycC3xVMA", "00:04:40", "2026-06-10", "DSY", ["DSY"], "small", "win", N, "", "", N, N, 1000, "not described", "high"),
("YDCycC3xVMA", "00:22:47", "2026-06-10", "CLWT", ["CLWT"], "main", "not stated", 2.59, ">08:00", "~08:00 (news at 8 a.m.)", N, N, N, "break of half dollar 2.50, add break of 3", "medium"),
# ---- 2026-06-17 9aVNE3mJJBk
("9aVNE3mJJBk", "00:11:16", "2026-06-12", "SpaceX (symbol not stated)", [], "?", "win", N, "", "", N, N, 10000, "IPO allocation", "medium"),
("9aVNE3mJJBk", "00:05:26", "2026-06-17", "CLWT", ["CLWT"], "main", "win", N, "", "", N, N, 7700, "blue sky, adds on micro pullback", "high"),
("9aVNE3mJJBk", "00:07:06", "2026-06-17", "UTSI", ["UTSI"], "main", "win", 6.50, "", "", N, 12000, 52000, "curl back up after pop to 7.50", "high"),
("9aVNE3mJJBk", "00:07:31", "2026-06-17", "UTSI", ["UTSI"], "main", "not stated", N, "", "", N, N, N, "dip buy; ABCD", "medium"),
("9aVNE3mJJBk", "00:08:09", "2026-06-17", "UTSI", ["UTSI"], "main", "not stated", N, "", "", N, N, N, "VWAP reclaim, add for break of highs", "medium"),
("9aVNE3mJJBk", "00:08:30", "2026-06-17", "WYHG", ["WYHG"], "main", "win", N, "", "", N, N, 300, "starter on scanner hit", "high"),
("9aVNE3mJJBk", "00:09:04", "2026-06-17", "ICCM", ["ICCM"], "main", "win", N, "", "", N, N, 15000, "micro pullback (third)", "high"),
("9aVNE3mJJBk", "00:09:14", "2026-06-17", "ICCM", ["ICCM"], "main", "loss", N, "", "", N, 20000, -20000, "pullback re-entry", "high"),
("9aVNE3mJJBk", "00:09:28", "2026-06-17", "ICCM", ["ICCM"], "main", "not stated", N, "", "", N, N, N, "curl back up; breaks of 7.50, 8, 9", "medium"),
("9aVNE3mJJBk", "00:03:25", "2026-06-17", "EHGO", ["EHGO"], "main", "loss", N, ">09:30", "after the opening bell", N, 20000, N, "first 1-min candle new high", "high"),
# ---- 2026-06-22 W6AErTREKHw
("W6AErTREKHw", "00:08:51", "2026-06-22", "NXTS", ["NXTS"], "small", "win", N, "<09:30", "pre-market", N, N, N, "pullback after high of 7.40", "high"),
("W6AErTREKHw", "00:09:29", "2026-06-22", "NXTS", ["NXTS"], "small", "win", N, "", "", N, N, N, "break back over VWAP after base", "medium"),
("W6AErTREKHw", "00:09:59", "2026-06-22", "NXTS", ["NXTS"], "small", "loss", N, "", "", N, N, -50, "break back over VWAP after base", "medium"),
("W6AErTREKHw", "00:11:32", "2026-06-22", "NXTS", ["NXTS"], "small", "win", N, "", "", N, N, N, "break over 9.50, 1-min", "high"),
("W6AErTREKHw", "00:11:48", "2026-06-22", "NXTS", ["NXTS"], "main", "not stated", N, "", "", N, N, N, "not stated", "low"),
# ---- 2026-06-25 A7Gnw1CMExI
("A7Gnw1CMExI", "00:03:36", "2026-06-25", "MIMI", ["MIMI"], "main", "win", N, "", "", N, N, N, "first push higher", "medium"),
("A7Gnw1CMExI", "00:04:01", "2026-06-25", "MIMI", ["MIMI"], "main", "not stated", N, "", "", N, N, N, "break of VWAP (re-entries)", "low"),
("A7Gnw1CMExI", "00:04:32", "2026-06-25", "MIMI", ["MIMI"], "main", "loss", N, "", "", N, 40000, -12000, "squeeze through 5", "high"),
("A7Gnw1CMExI", "00:06:28", "2026-06-25", "ANY", ["ANY"], "main", "loss", 3.90, ">08:56", "moments after the 08:56 MIMI loss", N, 13000, -6000, "news, entry near 4", "high"),
("A7Gnw1CMExI", "00:07:48", "2026-06-25", "ILLR", ["ILLR"], "main", "win", 1.90, "", "", N, 30000, 10000, "micro pullback; add for break of 2", "high"),
("A7Gnw1CMExI", "00:08:45", "2026-06-25", "ILLR", ["ILLR"], "main", "not stated", N, "", "", N, N, N, "small trades 2.40-2.90", "low"),
("A7Gnw1CMExI", "00:08:55", "2026-06-25", "ILLR", ["ILLR"], "main", "win", 2.50, ">09:00<09:30", "just before 09:30", N, N, N, "dip into the open", "high"),
("A7Gnw1CMExI", "00:09:14", "2026-06-25", "ILLR", ["ILLR"], "main", "loss", N, "", "", N, N, N, "halt resumption dip", "medium"),
("A7Gnw1CMExI", "00:09:19", "2026-06-25", "ILLR", ["ILLR"], "main", "not stated", N, "", "", N, N, N, "re-entry after halt resumption", "medium"),
# ---- 2026-06-26/28 S6AyP-2ziFc
("S6AyP-2ziFc", "00:03:07", "2026-06-26", "ZDAI", ["ZDAI"], "main", "loss", N, "", "", N, N, -25000, "first trade, really big size", "high"),
("S6AyP-2ziFc", "00:03:12", "2026-06-26", "SHPH", ["SHPH"], "main", "loss", N, "", "", N, N, N, "not stated", "high"),
("S6AyP-2ziFc", "00:01:03", "2026-06-26", "S. (likely SDOT)", ["SDOT"], "main", "win", N, "", "", N, N, N, "break through $10", "medium"),
# ---- 2026-06-30 b1pOO_bkbdA
("b1pOO_bkbdA", "00:01:56", "2026-06-30", "JEM", ["JEM"], "main", "not stated", N, "", "", N, N, N, "not described", "low"),
("b1pOO_bkbdA", "00:03:01", "2026-06-30", "SVRE", ["SVRE"], "small", "win", N, "", "", N, N, 200, "pullback", "high"),
("b1pOO_bkbdA", "00:03:17", "2026-06-30", "SVRE", ["SVRE"], "small", "win", N, "", "", N, N, 200, "dip buy off 8", "high"),
("b1pOO_bkbdA", "00:03:28", "2026-06-30", "SVRE", ["SVRE"], "small", "win", N, "", "", N, N, 200, "squeeze through 8/8.50/9", "high"),
("I0aTxFJWAD0", "00:02:37", "2026-07-02", "CLRO", ["CLRO"], "?", "not stated", N, "", "", N, N, N, "first little pop and pullback", "low"),
("0smkAvTc4AY", "00:00:23", "2026-07-06", "UNKNOWN", [], "?", "loss", N, "", "", N, N, -1600, "not stated", "low"),
("0smkAvTc4AY", "00:01:01", "2026-07-07", "CLRO", ["CLRO"], "?", "not stated", N, "", "", N, N, N, "not stated", "medium"),
("ChLgwLS9eJY", "00:00:17", "2026-07-13", "UNKNOWN", [], "small", "loss", N, "", "", N, N, N, "not stated", "low"),
("ChLgwLS9eJY", "00:03:15", "2026-07-14", "NXTC", ["NXTC"], "small", "win", N, "", "", N, N, 1400, "break over 8.40", "high"),
("ChLgwLS9eJY", "00:03:42", "2026-07-14", "NXTC", ["NXTC"], "main", "win", N, "", "", N, N, 19000, "micro pullbacks", "high"),
("ChLgwLS9eJY", "00:04:50", "2026-07-14", "UBXG", ["UBXG"], "small", "win", N, "", "", 10.40, N, 740.99, "micro pullback held over VWAP", "high"),
("PMNTB2WAiww", "00:00:35", "2026-07-16", "RUBY (spoken)", ["RUBI"], "small", "win", N, "", "", N, N, N, "tiny winner", "medium"),
# ---- 2026-07-22 YkEOx0ZWlWc
("YkEOx0ZWlWc", "00:04:40", "2026-07-22", "LABT", ["LABT"], "main", "win", N, "~08:05", "~08:05 (08:05-08:15 window)", N, N, 20000, "break through 3.60, adds into squeeze", "high"),
("YkEOx0ZWlWc", "00:05:18", "2026-07-22", "LABT", ["LABT"], "main", "not stated", N, "", "", N, N, N, "dip trades", "medium"),
("YkEOx0ZWlWc", "00:05:18b", "2026-07-22", "LABT", ["LABT"], "main", "not stated", N, "", "", N, N, N, "breakout add", "medium"),
("YkEOx0ZWlWc", "00:05:29", "2026-07-22", "LABT", ["LABT"], "main", "not stated", N, "", "", N, N, N, "break back over 5.50 and 6", "medium"),
("YkEOx0ZWlWc", "00:00:33", "2026-07-22", "LABT", ["LABT"], "small", "win", N, ">08:05<08:16", "08:05-08:15 window", N, N, 2242, "the same trade", "high"),
("p73Vmwgg64c", "00:01:45", "2026-07-23", "JEM", ["JEM"], "?", "not stated", N, "", "", N, N, N, "not stated", "low"),
("p73Vmwgg64c", "00:04:35", "2026-07-24", "EXYN", ["EXYN"], "main", "loss", N, "~07:20", "~07:20 (blue sky at 7:20)", N, N, -900, "blue sky, recent IPO", "medium"),
("p73Vmwgg64c", "00:05:41", "2026-07-24", "MSS", ["MSS"], "main", "win", N, "", "", N, N, 7000, "pullback after first squeeze", "high"),
("p73Vmwgg64c", "00:05:28", "2026-07-24", "MSS", ["MSS"], "small", "loss", N, "", "", N, N, N, "not stated", "low"),
# ---- 2026-07-27 Ht5j4VMdRMo
("Ht5j4VMdRMo", "00:03:14", "2026-07-27", "EDBL", ["EDBL"], "main", "loss", N, "", "", N, N, -3000, "pullback", "high"),
("Ht5j4VMdRMo", "00:03:23", "2026-07-27", "EDBL", ["EDBL"], "main", "loss", N, "", "", N, N, N, "re-entry, add over 8", "high"),
("Ht5j4VMdRMo", "00:04:12", "2026-07-27", "EDBL", ["EDBL"], "main", "win", N, "", "", N, N, N, "break of VWAP after curl", "high"),
("Ht5j4VMdRMo", "00:04:50", "2026-07-27", "EDBL", ["EDBL"], "main", "not stated", N, "", "", N, N, N, "a few trades", "low"),
("Ht5j4VMdRMo", "00:05:34", "2026-07-27", "VTIX", ["VTIX"], "main", "win", N, "", "", N, N, 1200, "micro pullback ~3.50 on breaking news", "high"),
("Ht5j4VMdRMo", "00:05:49", "2026-07-27", "VTIX", ["VTIX"], "small", "win", N, "", "", N, N, N, "not stated", "medium"),
# ---- 2026-07-28/29 SuY-q_OWMHw
("SuY-q_OWMHw", "00:01:58", "2026-07-28", "INLF", ["INLF"], "?", "loss", N, "", "", N, N, N, "not stated", "medium"),
("SuY-q_OWMHw", "00:17:03", "2026-07-28", "UNKNOWN", [], "small", "loss", N, "", "", N, N, N, "not stated", "low"),
("SuY-q_OWMHw", "00:08:19", "2026-07-29", "NCRA", ["NCRA"], "main", "win", 2.85, "", "", N, N, N, "curl back over VWAP / break over 3", "high"),
("SuY-q_OWMHw", "00:09:28", "2026-07-29", "NCRA", ["NCRA"], "main", "loss", N, "", "", N, 30000, -10000, "break through 4 (re-entry)", "high"),
("SuY-q_OWMHw", "00:09:42", "2026-07-29", "NCRA", ["NCRA"], "main", "not stated", N, "", "", N, N, N, "one more trade", "medium"),
("SuY-q_OWMHw", "00:10:54", "2026-07-29", "DFNS", ["DFNS"], "main", "loss", 39.00, ">09:30", "at/after the open", N, 1500, -1200, "break through the halt", "high"),
]

COLS = ("vid", "ts", "date", "raw_ticker", "cands", "acct", "outcome", "px", "tspec", "t_text",
        "exit", "shares", "pnl", "setup", "conf")


def rows():
    return [dict(zip(COLS, t)) for t in T]
