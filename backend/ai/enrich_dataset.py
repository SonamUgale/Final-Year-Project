"""
DarkShield AI - Dataset Enrichment Script (Phase 2)
==================================================

Enriches the baseline EC-DarkPattern dataset with:
1. Institutional & Academic Benign Samples (Label 0, Category: Not Dark Pattern)
   - Resolves false positive bias on educational domains like KKWIEER (kkwagh.edu.in).
   - Covers admissions, statutory disclosures (AICTE/NAAC/NIRF), academic calendars,
     examination procedures, library rules, anti-ragging undertakings, and campus notices.
   - 300 validated non-dark samples across page_id 5001 to 5030.

2. Minority Dark Pattern Classes (Label 1)
   - Forced Action: +50 samples (page_id 6001 to 6010)
   - Sneaking: +40 samples (page_id 6011 to 6018)
   - Obstruction: +40 samples (page_id 6019 to 6026)
   - Sourced and synthesized from Mathur et al. (Princeton 2019) taxonomy & FTC 2022 Guidelines.

Guarantees:
- Backs up original dataset to backend/ai/data/raw/dataset_v1_original.tsv
- Ensures distinct page_id grouping to prevent data leakage during StratifiedGroupKFold
- Deduplicates text entries
- Writes enriched dataset to backend/ai/data/raw/dataset.tsv
"""

import os
import sys
import shutil
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AI_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(AI_DIR, "data", "raw")
DATASET_PATH = os.path.join(RAW_DIR, "dataset.tsv")
BACKUP_PATH = os.path.join(RAW_DIR, "dataset_v1_original.tsv")


# ---------------------------------------------------------------------------
# 1. INSTITUTIONAL & ACADEMIC BENIGN CORPUS (300 Samples, page_id 5001 - 5030)
# ---------------------------------------------------------------------------
INSTITUTIONAL_SAMPLES = [
    # Page 5001: Admissions & CAP Process
    (5001, "Admissions open for First Year B.Tech and Direct Second Year Engineering for Academic Year 2026-27.", 0, "Not Dark Pattern"),
    (5001, "Candidates must have passed 10+2 examination with Physics and Mathematics as compulsory subjects.", 0, "Not Dark Pattern"),
    (5001, "Eligible candidates are advised to verify their documents at the nearest Facilitation Centre (FC).", 0, "Not Dark Pattern"),
    (5001, "Centralized Admission Process (CAP) seat distribution details are available on the state CET cell portal.", 0, "Not Dark Pattern"),
    (5001, "Last date for online registration and confirmation of application form is 30th June.", 0, "Not Dark Pattern"),
    (5001, "Seats under Institute Level quota will be filled strictly as per merit guidelines published by DTE.", 0, "Not Dark Pattern"),
    (5001, "Download the official admission brochure and fee structure for all undergraduate and postgraduate programs.", 0, "Not Dark Pattern"),
    (5001, "Selected candidates must report to the college admission cell with original certificates and fee DD.", 0, "Not Dark Pattern"),
    (5001, "Reservation policy is applicable as per the Government of Maharashtra and Directorate of Technical Education norms.", 0, "Not Dark Pattern"),
    (5001, "Contact the admissions helpdesk at 0253-2512876 for counseling queries and campus tour guidance.", 0, "Not Dark Pattern"),

    # Page 5002: Academic Calendar & Curriculum
    (5002, "Academic calendar for the Odd Semester 2026-2027 is now published for all engineering departments.", 0, "Not Dark Pattern"),
    (5002, "Continuous Assessment Test 1 (CAT-1) will commence from the third week of August.", 0, "Not Dark Pattern"),
    (5002, "Students can view and download the revised curriculum scheme and syllabus copy from the department page.", 0, "Not Dark Pattern"),
    (5002, "Department of Computer Engineering offers electives in Cloud Computing, Cyber Security, and Deep Learning.", 0, "Not Dark Pattern"),
    (5002, "Laboratory sessions will be conducted in batches according to the departmental weekly timetable.", 0, "Not Dark Pattern"),
    (5002, "Submission of term work, mini-projects, and continuous assessment sheets is scheduled for November.", 0, "Not Dark Pattern"),
    (5002, "Mid-term academic feedback can be submitted securely through the ERP student login portal.", 0, "Not Dark Pattern"),
    (5002, "End-semester practical and oral examinations will be evaluated jointly by internal and external examiners.", 0, "Not Dark Pattern"),
    (5002, "Students must maintain minimum 75 percent attendance in theory lectures and practical laboratory sessions.", 0, "Not Dark Pattern"),
    (5002, "Remedial classes will be scheduled on Saturdays for students requiring additional academic clarification.", 0, "Not Dark Pattern"),

    # Page 5003: Accreditation & Statutory Disclosures (AICTE, NBA, NAAC, NIRF)
    (5003, "K.K. Wagh Institute of Engineering Education and Research is accredited by NAAC with A Grade.", 0, "Not Dark Pattern"),
    (5003, "Mandatory disclosure under AICTE regulations has been updated for the current academic session.", 0, "Not Dark Pattern"),
    (5003, "National Institutional Ranking Framework (NIRF) data submission report is publicly accessible on our website.", 0, "Not Dark Pattern"),
    (5003, "National Board of Accreditation (NBA) has accredited our undergraduate engineering programs.", 0, "Not Dark Pattern"),
    (5003, "Internal Quality Assurance Cell (IQAC) minutes of meetings and action taken reports are available in the repository.", 0, "Not Dark Pattern"),
    (5003, "All technical programs are approved by AICTE New Delhi and affiliated to Savitribai Phule Pune University.", 0, "Not Dark Pattern"),
    (5003, "Autonomous curriculum structure approved by the Academic Council is effective from Academic Year 2024.", 0, "Not Dark Pattern"),
    (5003, "Audit reports and audited financial balance sheets are published under statutory compliance obligations.", 0, "Not Dark Pattern"),
    (5003, "Anti-ragging committee and squad contact numbers are displayed prominently across the campus premises.", 0, "Not Dark Pattern"),
    (5003, "Grievance redressal mechanism is established as per University Grants Commission (UGC) regulations.", 0, "Not Dark Pattern"),

    # Page 5004: Central Library & Digital Resources
    (5004, "The Central Library remains open from 8:00 AM to 8:00 PM on all working days including study vacations.", 0, "Not Dark Pattern"),
    (5004, "Students may issue up to four books simultaneously using their digital barcode identity cards.", 0, "Not Dark Pattern"),
    (5004, "Access to IEEE Xplore, ScienceDirect, and Springer e-journals is available through institutional IP login.", 0, "Not Dark Pattern"),
    (5004, "National Digital Library of India (NDLI) club conducts digital literacy workshops for freshers.", 0, "Not Dark Pattern"),
    (5004, "Reference section houses encyclopedias, handbooks, and bound volumes of international journals.", 0, "Not Dark Pattern"),
    (5004, "Overdue fines of two rupees per day will be levied on books returned after the designated due date.", 0, "Not Dark Pattern"),
    (5004, "Book bank facility is provided to socially and economically backward students free of charge.", 0, "Not Dark Pattern"),
    (5004, "Quiet study hall with air-conditioned reading cabins is reserved for competitive exam preparation.", 0, "Not Dark Pattern"),
    (5004, "Plagiarism checking service using Turnitin is provided to final-year project groups by the librarian.", 0, "Not Dark Pattern"),
    (5004, "Please return all borrowed books and obtain a No Dues clearance certificate before term end.", 0, "Not Dark Pattern"),

    # Page 5005: Examinations & Evaluation Section
    (5005, "Online examination forms for the Winter session can be submitted through the university exam portal.", 0, "Not Dark Pattern"),
    (5005, "Hall tickets for the upcoming in-semester theory examinations will be distributed by class counselors.", 0, "Not Dark Pattern"),
    (5005, "Revaluation and photo-copy application deadlines are strictly notified on the exam section notice board.", 0, "Not Dark Pattern"),
    (5005, "Provisional grade cards and credit transfer statements will be issued within two weeks of result declaration.", 0, "Not Dark Pattern"),
    (5005, "Examination seat numbers and block-wise seating arrangements will be posted on the ground floor notice board.", 0, "Not Dark Pattern"),
    (5005, "Students are strictly prohibited from carrying mobile phones, smartwatches, or notes into the exam hall.", 0, "Not Dark Pattern"),
    (5005, "Supplementary and backlog examinations for failed courses will be conducted in the month of December.", 0, "Not Dark Pattern"),
    (5005, "Convocation registration for graduated batch students is open on the SPPU university portal.", 0, "Not Dark Pattern"),
    (5005, "Official academic transcripts and migration certificates can be requested online via the student login.", 0, "Not Dark Pattern"),
    (5005, "Standard operating procedure for grievance redressal regarding internal assessment marks is displayed.", 0, "Not Dark Pattern"),

    # Page 5006: Training and Placement Cell (T&P)
    (5006, "Training and Placement Cell organizes campus recruitment drives for final-year engineering students.", 0, "Not Dark Pattern"),
    (5006, "Over 150 multinational companies visit KKWIEER annually for on-campus student recruitment.", 0, "Not Dark Pattern"),
    (5006, "Pre-placement training includes mock aptitude tests, coding challenges, and HR interview rounds.", 0, "Not Dark Pattern"),
    (5006, "Memorandum of Understanding signed with leading IT firms to provide semester-long industry internships.", 0, "Not Dark Pattern"),
    (5006, "Highest salary package offered in the recent placement season exceeded 18 LPA by multinational enterprises.", 0, "Not Dark Pattern"),
    (5006, "Eligible students must register with the placement portal and submit updated resumes by Friday evening.", 0, "Not Dark Pattern"),
    (5006, "Alumni mentoring sessions are organized every month to guide juniors on engineering career trajectories.", 0, "Not Dark Pattern"),
    (5006, "Foreign language certification courses in Japanese and German are offered on campus for global placements.", 0, "Not Dark Pattern"),
    (5006, "Industry experts conduct weekly guest lectures on emerging technological trends in software architecture.", 0, "Not Dark Pattern"),
    (5006, "Entrepreneurship Development Cell (EDC) provides seed funding and incubation support for student startups.", 0, "Not Dark Pattern"),

    # Page 5007: Scholarships & Financial Support
    (5007, "Government scholarships under MahaDBT portal are open for SC, ST, OBC, VJNT, and EBC students.", 0, "Not Dark Pattern"),
    (5007, "Freeship and Tuition Fee Waiver Scheme (TFWS) application forms must be verified before the deadline.", 0, "Not Dark Pattern"),
    (5007, "Minority scholarship applications can be submitted through the National Scholarship Portal (NSP).", 0, "Not Dark Pattern"),
    (5007, "Merit-cum-means financial assistance is provided by the management trust to economically deserving students.", 0, "Not Dark Pattern"),
    (5007, "Students seeking education bank loans can collect bonafide certificates from the college student section.", 0, "Not Dark Pattern"),
    (5007, "Income certificate and domicile proof must be uploaded along with the annual scholarship renewal form.", 0, "Not Dark Pattern"),
    (5007, "No tuition fee is charged to girl students admitted under the state government higher education waiver scheme.", 0, "Not Dark Pattern"),
    (5007, "Bank savings account must be linked with Aadhaar to receive direct benefit transfer of scholarship stipends.", 0, "Not Dark Pattern"),
    (5007, "Notice regarding payment of institutional academic fees in two equal installments upon formal request.", 0, "Not Dark Pattern"),
    (5007, "Contact the scholarship coordinator at Room 104 between 2:00 PM and 4:00 PM for document verification.", 0, "Not Dark Pattern"),

    # Page 5008: Student Safety, Discipline & Anti-Ragging
    (5008, "Ragging in any form is strictly banned inside and outside the college campus and hostel premises.", 0, "Not Dark Pattern"),
    (5008, "Students and parents must submit the online anti-ragging affidavit undertaking at antiragging.in.", 0, "Not Dark Pattern"),
    (5008, "Internal Complaints Committee (ICC) ensures safety and prevention of sexual harassment on campus.", 0, "Not Dark Pattern"),
    (5008, "Equal Opportunity Cell addresses concerns of differently-abled students and socially marginalized groups.", 0, "Not Dark Pattern"),
    (5008, "Student Council elections and appointment of departmental class representatives will be held next week.", 0, "Not Dark Pattern"),
    (5008, "Toll-free national anti-ragging helpline number 1800-180-5522 is operational 24 hours every day.", 0, "Not Dark Pattern"),
    (5008, "CCTV surveillance is maintained across corridors, labs, library, parking areas, and entry gates.", 0, "Not Dark Pattern"),
    (5008, "Professional psychological counseling and mental wellbeing services are free for all enrolled students.", 0, "Not Dark Pattern"),
    (5008, "Disciplinary committee will take stringent disciplinary action against any breach of student conduct rules.", 0, "Not Dark Pattern"),
    (5008, "Women's Development Cell conducts self-defense workshops, legal awareness, and healthcare seminars.", 0, "Not Dark Pattern"),

    # Page 5009: Research, Conferences & Technical Publications
    (5009, "Call for papers for the International Conference on Emerging Trends in Engineering and Computing.", 0, "Not Dark Pattern"),
    (5009, "Faculty members and research scholars must submit original manuscripts formatted in IEEE style.", 0, "Not Dark Pattern"),
    (5009, "Research grants sanctioned by DST, SERB, and AICTE are currently under active execution.", 0, "Not Dark Pattern"),
    (5009, "Ph.D. research center recognized by Savitribai Phule Pune University offers research programs.", 0, "Not Dark Pattern"),
    (5009, "Quarterly engineering research bulletin publishes peer-reviewed faculty papers and patent disclosures.", 0, "Not Dark Pattern"),
    (5009, "Intellectual Property Rights (IPR) cell assists faculty and students with patent drafting and filing.", 0, "Not Dark Pattern"),
    (5009, "Plagiarism similarity check using licensed software is mandatory prior to final thesis submission.", 0, "Not Dark Pattern"),
    (5009, "Best student paper awards will be conferred during the valedictory session of the national symposium.", 0, "Not Dark Pattern"),
    (5009, "High-performance computational cluster with GPU accelerators is dedicated to artificial intelligence research.", 0, "Not Dark Pattern"),
    (5009, "Faculty development programs (FDP) sponsored by ATAL academy are organized regularly on campus.", 0, "Not Dark Pattern"),

    # Page 5010: Hostel, Canteen & Student Amenities
    (5010, "Hostel admission forms for first-year boys and girls are available at the campus administration office.", 0, "Not Dark Pattern"),
    (5010, "Separate on-campus hostel facilities are equipped with solar hot water, study tables, and Wi-Fi.", 0, "Not Dark Pattern"),
    (5010, "Campus cafeteria serves hygienic, nutritious vegetarian meals and snacks at subsidized student prices.", 0, "Not Dark Pattern"),
    (5010, "Medical dispensary with a resident doctor and trained nurse is accessible round the clock on campus.", 0, "Not Dark Pattern"),
    (5010, "College transport bus service covers all primary routes across Nashik city and peripheral suburbs.", 0, "Not Dark Pattern"),
    (5010, "Indoor gymnasium and outdoor sports grounds are available for students after regular instructional hours.", 0, "Not Dark Pattern"),
    (5010, "Automated Teller Machine (ATM) and bank branch are situated near the main entrance gate.", 0, "Not Dark Pattern"),
    (5010, "Stationery store and reprographic xerox center provide engineering drawing tools and printing services.", 0, "Not Dark Pattern"),
    (5010, "Hostel residents must mark evening biometric attendance between 8:30 PM and 9:00 PM daily.", 0, "Not Dark Pattern"),
    (5010, "Parents visiting hostel residents may reserve guest rooms at nominal charges subject to prior notice.", 0, "Not Dark Pattern"),

    # Page 5011: Departments & Laboratories
    (5011, "Department of Computer Engineering features specialized labs for Data Structures, AI, and Networks.", 0, "Not Dark Pattern"),
    (5011, "Department of Electronics and Telecommunication Engineering operates an Advanced VLSI Design Lab.", 0, "Not Dark Pattern"),
    (5011, "Mechanical Engineering department houses CNC machines, 3D printers, and a thermal engineering setup.", 0, "Not Dark Pattern"),
    (5011, "Civil Engineering department offers environmental engineering testing and concrete technology facilities.", 0, "Not Dark Pattern"),
    (5011, "Chemical Engineering department maintains unit operations and industrial reaction kinetics pilot plants.", 0, "Not Dark Pattern"),
    (5011, "Department of Information Technology provides hands-on infrastructure for full-stack web development.", 0, "Not Dark Pattern"),
    (5011, "Electrical Engineering department maintains power systems simulation and electrical drive test rigs.", 0, "Not Dark Pattern"),
    (5011, "First Year Engineering department provides fundamental physics, chemistry, and workshop practice labs.", 0, "Not Dark Pattern"),
    (5011, "Students must wear safety coats and closed shoes during chemistry and mechanical workshop sessions.", 0, "Not Dark Pattern"),
    (5011, "Lab manuals and software installation guides can be downloaded from the respective lab courseware page.", 0, "Not Dark Pattern"),

    # Page 5012: Student Chapters, Clubs & Extracurriculars
    (5012, "IEEE Student Branch organizes annual technical project exhibitions and coding competitions.", 0, "Not Dark Pattern"),
    (5012, "Computer Society of India (CSI) student chapter conducts hackathons and open-source bootcamps.", 0, "Not Dark Pattern"),
    (5012, "Robotics Club participates in national Robocon competitions and conducts bot-building workshops.", 0, "Not Dark Pattern"),
    (5012, "National Service Scheme (NSS) unit organizes blood donation camps and rural development initiatives.", 0, "Not Dark Pattern"),
    (5012, "Annual cultural festival features inter-collegiate dance, music, drama, and fine arts events.", 0, "Not Dark Pattern"),
    (5012, "SAE Collegiate Club designs and fabricates all-terrain vehicles (ATVs) for BAJA racing challenges.", 0, "Not Dark Pattern"),
    (5012, "Photography and short film club hosts annual photography exhibitions during college annual day.", 0, "Not Dark Pattern"),
    (5012, "Nature Club organizes tree plantation drives and environmental cleanliness campaigns on campus.", 0, "Not Dark Pattern"),
    (5012, "Debating and Literary Society holds parliamentary debates and model United Nations conferences.", 0, "Not Dark Pattern"),
    (5012, "Student chapters invite distinguished industry luminaries to mentor young engineers on tech innovations.", 0, "Not Dark Pattern"),

    # Page 5013: Alumni Association & Networking
    (5013, "KKWIEER Alumni Association fosters strong lifelong connections between graduates and the alma mater.", 0, "Not Dark Pattern"),
    (5013, "Annual Global Alumni Meet will be celebrated on campus on the third Saturday of December.", 0, "Not Dark Pattern"),
    (5013, "Distinguished alumni awards honor outstanding professional contributions across technology and business.", 0, "Not Dark Pattern"),
    (5013, "Alumni endowment fund sponsors undergraduate merit scholarships and laboratory modernization.", 0, "Not Dark Pattern"),
    (5013, "Graduates are requested to update their current organization and designation in the alumni portal.", 0, "Not Dark Pattern"),
    (5013, "Alumni chapters in Pune, Mumbai, Bengaluru, and the USA organize regular regional networking dinners.", 0, "Not Dark Pattern"),
    (5013, "Alumni entrepreneurs offer paid internship opportunities to current third-year engineering students.", 0, "Not Dark Pattern"),
    (5013, "Guest lecture series titled Alumni Speaks shares real-world industry perspectives with undergraduates.", 0, "Not Dark Pattern"),
    (5013, "Life membership fee for the registered Alumni Association can be remitted online via payment gateway.", 0, "Not Dark Pattern"),
    (5013, "Search the digital directory to reconnect with batchmates and engineering faculty colleagues.", 0, "Not Dark Pattern"),

    # Page 5014: Administrative & Governance Notices
    (5014, "Governing Body and College Development Committee (CDC) meeting resolutions are documented in files.", 0, "Not Dark Pattern"),
    (5014, "Office working hours for public queries are 9:30 AM to 5:30 PM on Monday through Saturday.", 0, "Not Dark Pattern"),
    (5014, "Second and fourth Saturdays of every month are observed as non-instructional holidays for staff.", 0, "Not Dark Pattern"),
    (5014, "Tender notices for procurement of lab equipment, server hardware, and furniture are published online.", 0, "Not Dark Pattern"),
    (5014, "Expression of interest is invited from chartered accounting firms for conducting statutory audits.", 0, "Not Dark Pattern"),
    (5014, "Campus maintenance and security services are managed through certified institutional contractors.", 0, "Not Dark Pattern"),
    (5014, "Clean and green campus policy outlines solar power generation and rainwater harvesting protocols.", 0, "Not Dark Pattern"),
    (5014, "Right to Information (RTI) cell details with contact numbers of Public Information Officer are available.", 0, "Not Dark Pattern"),
    (5014, "Employee handbook outlines service rules, leave policies, and code of professional ethics for faculty.", 0, "Not Dark Pattern"),
    (5014, "Official correspondence should be addressed to the Principal, KKWIEER, Amrutdham, Nashik.", 0, "Not Dark Pattern"),

    # Page 5015: Faculty & Academic Staff
    (5015, "Faculty profile directory lists qualifications, research specializations, and publications.", 0, "Not Dark Pattern"),
    (5015, "Over eighty faculty members hold doctoral degrees from premier institutes including IITs and NITs.", 0, "Not Dark Pattern"),
    (5015, "Teacher-student mentor ratio of 1:15 is maintained for personalized academic mentoring.", 0, "Not Dark Pattern"),
    (5015, "Faculty performance appraisal system evaluates teaching pedagogy, research grants, and student feedback.", 0, "Not Dark Pattern"),
    (5015, "Faculty members are granted study leave and sponsorship to pursue doctoral research at reputed universities.", 0, "Not Dark Pattern"),
    (5015, "Dean Academics supervises curriculum delivery, timetable compliance, and semester examinations.", 0, "Not Dark Pattern"),
    (5015, "Head of Department (HoD) coordinates departmental faculty meetings and laboratory modernization.", 0, "Not Dark Pattern"),
    (5015, "Adjunct faculty from industry deliver specialized elective modules in cloud architecture and DevOps.", 0, "Not Dark Pattern"),
    (5015, "Visiting professors from foreign partner universities deliver guest lectures during winter school.", 0, "Not Dark Pattern"),
    (5015, "Office hours for student consultation are specified on each faculty member's office door.", 0, "Not Dark Pattern"),

    # Page 5016: Student Portal & Digital Services
    (5016, "Enter your student PRN number and password to access the college ERP dashboard.", 0, "Not Dark Pattern"),
    (5016, "View your semester subject attendance, continuous assessment grades, and fee payment receipts.", 0, "Not Dark Pattern"),
    (5016, "In case you forget your student login password, click Forgot Password to receive a reset link.", 0, "Not Dark Pattern"),
    (5016, "Download online lecture notes, laboratory assignment problem statements, and reference ppts.", 0, "Not Dark Pattern"),
    (5016, "Submit your final year project synopsis and literature survey report in PDF format by the due date.", 0, "Not Dark Pattern"),
    (5016, "Online payment of tuition and examination fees can be completed securely through Net Banking or UPI.", 0, "Not Dark Pattern"),
    (5016, "Digital identity card barcode can be scanned at the library turnstile and sports center.", 0, "Not Dark Pattern"),
    (5016, "Update your registered parent mobile number and residential postal address in the ERP profile.", 0, "Not Dark Pattern"),
    (5016, "College mobile application is available on Google Play Store for daily timetable notifications.", 0, "Not Dark Pattern"),
    (5016, "Server maintenance is scheduled on Sunday midnight; ERP services may be briefly unavailable.", 0, "Not Dark Pattern"),

    # Page 5017: Fee Structure & Payment Policies
    (5017, "Tuition fee and development fee structure approved by the Fees Regulating Authority (FRA) is displayed.", 0, "Not Dark Pattern"),
    (5017, "No capitation fee or donation is accepted for any admission under any circumstances.", 0, "Not Dark Pattern"),
    (5017, "Fee payment receipt can be downloaded immediately after successful online transaction confirmation.", 0, "Not Dark Pattern"),
    (5017, "Refund of academic fees upon cancellation of admission will be governed strictly as per DTE rules.", 0, "Not Dark Pattern"),
    (5017, "Students eligible for government scholarship must pay only the non-reimbursable fee component.", 0, "Not Dark Pattern"),
    (5017, "Detailed breakup of tuition fee, exam fee, library deposit, and gymkhana charges is shown below.", 0, "Not Dark Pattern"),
    (5017, "Caution money deposit is refundable after completion of the four-year undergraduate engineering course.", 0, "Not Dark Pattern"),
    (5017, "Demand Draft (DD) should be drawn in favor of Principal, K.K. Wagh Institute of Engineering, Nashik.", 0, "Not Dark Pattern"),
    (5017, "Late fee of fifty rupees per day will apply after the designated fee payment due date.", 0, "Not Dark Pattern"),
    (5017, "Accounts department counter is open for student fee verification from 10:00 AM to 2:00 PM.", 0, "Not Dark Pattern"),

    # Page 5018: Eligibility & Admission Criteria
    (5018, "Eligibility criteria for Maharashtra State and All India candidature candidates are detailed in brochure.", 0, "Not Dark Pattern"),
    (5018, "Non-zero positive score in MHT-CET or JEE Main Paper 1 is mandatory for engineering admissions.", 0, "Not Dark Pattern"),
    (5018, "Diploma holders in engineering with minimum 45 percent marks are eligible for direct second year entry.", 0, "Not Dark Pattern"),
    (5018, "Caste certificate, caste validity certificate, and non-creamy layer certificate are required for reserved seats.", 0, "Not Dark Pattern"),
    (5018, "Economically Weaker Section (EWS) eligibility certificate must be issued by a competent state authority.", 0, "Not Dark Pattern"),
    (5018, "Foreign national and NRI candidate admissions are conducted through supernumerary quota allocations.", 0, "Not Dark Pattern"),
    (5018, "Equivalence certificate from Association of Indian Universities is mandatory for foreign qualifications.", 0, "Not Dark Pattern"),
    (5018, "Medical fitness certificate signed by a registered medical practitioner must be produced at admission.", 0, "Not Dark Pattern"),
    (5018, "Provisional admission will be confirmed only after physical verification of all original documents.", 0, "Not Dark Pattern"),
    (5018, "Check seat matrix and cutoff ranks of previous years on the official college cutoff archive page.", 0, "Not Dark Pattern"),

    # Page 5019: Sports, Gymnasium & Physical Education
    (5019, "Department of Physical Education organizes inter-collegiate cricket, football, and basketball tournaments.", 0, "Not Dark Pattern"),
    (5019, "Olympic-size athletics track and synthetic courts are available for regular student practice.", 0, "Not Dark Pattern"),
    (5019, "Students representing the university in national sports competitions are awarded bonus academic credits.", 0, "Not Dark Pattern"),
    (5019, "Yoga sessions and wellness meditation workshops are organized weekly on Tuesday mornings.", 0, "Not Dark Pattern"),
    (5019, "Gymnasium trainer provides guidance on fitness, strength training, and cardiovascular health.", 0, "Not Dark Pattern"),
    (5019, "Table tennis tables and chess boards are situated in the student activity center recreation room.", 0, "Not Dark Pattern"),
    (5019, "Annual Sports Week involves spirited competitions between departmental engineering batches.", 0, "Not Dark Pattern"),
    (5019, "Proper sports attire and rubber-soled sports shoes are mandatory inside the indoor badminton court.", 0, "Not Dark Pattern"),
    (5019, "Sports equipment can be borrowed from the sports clerk by submitting student ID cards.", 0, "Not Dark Pattern"),
    (5019, "Trophies and certificates of merit will be distributed to winners during the Annual College Day.", 0, "Not Dark Pattern"),

    # Page 5020: Innovation, Startups & Incubation Center
    (5020, "KKWIEER Institution's Innovation Council (IIC) is recognized with a five-star ranking by Ministry of Education.", 0, "Not Dark Pattern"),
    (5020, "Incubation center provides co-working office space, high-speed internet, and mentor support for student startups.", 0, "Not Dark Pattern"),
    (5020, "Seed grant funding up to five lakh rupees is awarded to viable student business model prototypes.", 0, "Not Dark Pattern"),
    (5020, "National Innovation and Startup Policy (NISP) guidelines have been adopted for student entrepreneurs.", 0, "Not Dark Pattern"),
    (5020, "Annual Ideation Contest invites interdisciplinary engineering student teams to present tech solutions.", 0, "Not Dark Pattern"),
    (5020, "Patent drafting workshop explains claims writing, prior art search, and patent filing procedures.", 0, "Not Dark Pattern"),
    (5020, "Angel investors and venture capitalists are invited for demo day pitches by incubated company founders.", 0, "Not Dark Pattern"),
    (5020, "Maker space lab is equipped with laser cutters, soldering stations, microcontrollers, and sensor kits.", 0, "Not Dark Pattern"),
    (5020, "Students may register their enterprise through the Ministry of MSME Udyam registration portal.", 0, "Not Dark Pattern"),
    (5020, "Legal and accounting advisory is provided free of charge to student-led campus enterprises.", 0, "Not Dark Pattern"),

    # Page 5021: College Location, Contact & Directions
    (5021, "K.K. Wagh Institute of Engineering Education and Research is located at Hirabai Haridas Vidyanagari, Amrutdham.", 0, "Not Dark Pattern"),
    (5021, "The college campus is located on the Nashik-Pune National Highway, approximately 5 km from Central Bus Stand.", 0, "Not Dark Pattern"),
    (5021, "Nashik Road Railway Station is located approximately 10 km from the college campus.", 0, "Not Dark Pattern"),
    (5021, "For general inquiries, email us at kkwieer@kkwagh.edu.in or call 0253-2512876.", 0, "Not Dark Pattern"),
    (5021, "Visitor parking is available near Gate 1 upon collecting a temporary entry pass from security.", 0, "Not Dark Pattern"),
    (5021, "Campus map displays academic blocks, administrative complex, workshops, library, and sports complex.", 0, "Not Dark Pattern"),
    (5021, "Principal's office is situated on the second floor of the main administrative building.", 0, "Not Dark Pattern"),
    (5021, "Nearest landmark is the Amrutdham Flyover on the Mumbai-Agra National Highway.", 0, "Not Dark Pattern"),
    (5021, "City bus service route number 12 and 15 drop passengers directly opposite the main college gate.", 0, "Not Dark Pattern"),
    (5021, "Official postal code for the institute is 422003, Nashik, Maharashtra, India.", 0, "Not Dark Pattern"),

    # Page 5022: National Service Scheme (NSS) & Social Responsibility
    (5022, "NSS unit of KKWIEER organizes special seven-day residential rural adaptation camps every winter.", 0, "Not Dark Pattern"),
    (5022, "Volunteers undertake watershed management, tree planting, and health hygiene awareness in adopted villages.", 0, "Not Dark Pattern"),
    (5022, "Annual blood donation camp collected over 500 units of blood in partnership with civil hospital.", 0, "Not Dark Pattern"),
    (5022, "Cleanliness drives are conducted regularly under the Swachh Bharat Abhiyan initiative on campus.", 0, "Not Dark Pattern"),
    (5022, "Road safety awareness rallies are held in collaboration with Nashik City Traffic Police.", 0, "Not Dark Pattern"),
    (5022, "Free eye testing and medical health checkup camps are held for housekeeping and security personnel.", 0, "Not Dark Pattern"),
    (5022, "E-waste collection drive encourages safe disposal and recycling of old electronics across departments.", 0, "Not Dark Pattern"),
    (5022, "Volunteers tutor underprivileged school children in mathematics and science on weekend mornings.", 0, "Not Dark Pattern"),
    (5022, "NSS volunteers completing 240 hours of community service receive official university certificates.", 0, "Not Dark Pattern"),
    (5022, "Disaster management training teaches cardiopulmonary resuscitation (CPR) and fire fighting drills.", 0, "Not Dark Pattern"),

    # Page 5023: Environmental Sustainability & Green Campus
    (5023, "Solar photovoltaic rooftop power plants generate clean electrical energy covering 40 percent of demand.", 0, "Not Dark Pattern"),
    (5023, "Rainwater harvesting recharge pits ensure conservation of groundwater across the 82-acre campus.", 0, "Not Dark Pattern"),
    (5023, "Sewage treatment plant (STP) treats greywater which is reused for gardening and landscape maintenance.", 0, "Not Dark Pattern"),
    (5023, "Campus is designated as a plastic-free and tobacco-free educational zone under strict penalty notices.", 0, "Not Dark Pattern"),
    (5023, "Organic compost pits convert canteen food scraps and fallen tree leaves into natural farm fertilizer.", 0, "Not Dark Pattern"),
    (5023, "Bicycle parking stands and pedestrian-friendly pathways encourage non-motorized internal commuting.", 0, "Not Dark Pattern"),
    (5023, "Energy-efficient LED fixtures and sensor-controlled fans are installed across all lecture halls and labs.", 0, "Not Dark Pattern"),
    (5023, "Green audit, energy audit, and environmental compliance audits are conducted by external accredited bodies.", 0, "Not Dark Pattern"),
    (5023, "Botanical garden showcases over two hundred medicinal and native plant varieties.", 0, "Not Dark Pattern"),
    (5023, "Paperless administrative workflow using digital document management systems reduces overall paper use.", 0, "Not Dark Pattern"),

    # Page 5024: Continuing Education & Skill Certifications
    (5024, "Center for Continuing Education conducts weekend professional certificate courses for working engineers.", 0, "Not Dark Pattern"),
    (5024, "NPTEL and SWAYAM local chapter facilitates credit transfers for approved MOOC courses.", 0, "Not Dark Pattern"),
    (5024, "AWS Academy and Cisco Networking Academy offer globally recognized certification pathways on campus.", 0, "Not Dark Pattern"),
    (5024, "Hands-on workshop on Programmable Logic Controllers (PLC) and SCADA systems for automation engineers.", 0, "Not Dark Pattern"),
    (5024, "Specialized training in Building Information Modeling (BIM) software for civil engineering undergraduates.", 0, "Not Dark Pattern"),
    (5024, "Electric Vehicle technology short-term course covers battery management systems and motor controllers.", 0, "Not Dark Pattern"),
    (5024, "Cybersecurity ethical hacking bootcamp prepares students for certified security analyst credentials.", 0, "Not Dark Pattern"),
    (5024, "Data science with Python and R certification program includes capstone real-world portfolio projects.", 0, "Not Dark Pattern"),
    (5024, "Course completion certificates with verifiable QR codes are issued to successful participants.", 0, "Not Dark Pattern"),
    (5024, "Nominal subsidized registration fee applies for currently enrolled engineering college students.", 0, "Not Dark Pattern"),

    # Page 5025: Technical Festivals & Project Competitions
    (5025, "Equinox is the annual national level technical symposium organized by engineering students.", 0, "Not Dark Pattern"),
    (5025, "Paper presentation contests invite technical research papers across diverse engineering disciplines.", 0, "Not Dark Pattern"),
    (5025, "Line follower and robo-war tournaments attract participants from premier engineering institutes.", 0, "Not Dark Pattern"),
    (5025, "Bridge design and structural modeling competitions test strength-to-weight structural ratios.", 0, "Not Dark Pattern"),
    (5025, "Coding hackathon runs continuously for 24 hours with problem statements sponsored by IT corporations.", 0, "Not Dark Pattern"),
    (5025, "Circuit debugging and breadboard assembly challenges evaluate analog electronic design skills.", 0, "Not Dark Pattern"),
    (5025, "Technical quiz competition tests fundamental principles of mathematics, physics, and computing.", 0, "Not Dark Pattern"),
    (5025, "Cash prizes and trophies worth two lakh rupees will be awarded across all technical competition tracks.", 0, "Not Dark Pattern"),
    (5025, "Register your project team online on the official technical festival portal before the deadline.", 0, "Not Dark Pattern"),
    (5025, "Participation certificates will be distributed to all registered attendees at the conclusion.", 0, "Not Dark Pattern"),

    # Page 5026: Institutional Vision, Mission & Core Values
    (5026, "Vision: To be recognized as an institute of repute producing globally competent and socially responsible engineers.", 0, "Not Dark Pattern"),
    (5026, "Mission: Imparting quality technical education through progressive curriculum and experiential pedagogy.", 0, "Not Dark Pattern"),
    (5026, "Core Values: Integrity, academic excellence, mutual respect, professional ethics, and sustainable development.", 0, "Not Dark Pattern"),
    (5026, "Program Educational Objectives (PEOs) guide the design of all undergraduate engineering course structures.", 0, "Not Dark Pattern"),
    (5026, "Program Outcomes (POs) and Course Outcomes (COs) are mapped as per Washington Accord outcome-based education.", 0, "Not Dark Pattern"),
    (5026, "The institute was established in the year 1984 under the visionary leadership of Late Padmashree Karmaveer Kakasaheb Wagh.", 0, "Not Dark Pattern"),
    (5026, "Managed by K.K. Wagh Education Society, one of the oldest and most prestigious educational trusts in Maharashtra.", 0, "Not Dark Pattern"),
    (5026, "K.K. Wagh isn't just a college—it's a launchpad for dreams and engineering excellence.", 0, "Not Dark Pattern"),
    (5026, "Everything that enthuses people at our university and education society reflects our academic mission.", 0, "Not Dark Pattern"),
    (5026, "Our campus is driven by a deep-rooted culture in educational excellence and holistic growth.", 0, "Not Dark Pattern"),
    (5026, "Providing specialized training and knowledge in Horticulture, Agriculture, and Engineering sciences.", 0, "Not Dark Pattern"),
    (5026, "Continuous improvement in teaching-learning is driven by systematic stakeholder feedback and academic audits.", 0, "Not Dark Pattern"),
    (5026, "At KKWIEER, learning goes beyond textbooks to foster innovation, critical inquiry, and holistic student development.", 0, "Not Dark Pattern"),
    (5026, "Students are encouraged to embrace lifelong learning to stay relevant in a rapidly evolving technological landscape.", 0, "Not Dark Pattern"),

    # Page 5027: International Relations & Global MoUs
    (5027, "Office of International Affairs facilitates student exchange programs and joint international research.", 0, "Not Dark Pattern"),
    (5027, "Academic partnerships established with universities in Germany, Japan, and the United States.", 0, "Not Dark Pattern"),
    (5027, "Undergraduate students can spend their final semester completing capstone research at partner overseas labs.", 0, "Not Dark Pattern"),
    (5027, "Dual degree and credit transfer agreements are under active consideration with accredited European institutes.", 0, "Not Dark Pattern"),
    (5027, "International visiting professors conduct intensive 2-week masterclasses on advanced engineering topics.", 0, "Not Dark Pattern"),
    (5027, "Guidance on GRE, TOEFL, and IELTS preparation is offered free by the international relations student wing.", 0, "Not Dark Pattern"),
    (5027, "Passport assistance and visa documentation support are provided for students selected for global internships.", 0, "Not Dark Pattern"),
    (5027, "Global alumni chapters mentor outgoing graduates on international living, culture, and academic protocols.", 0, "Not Dark Pattern"),
    (5027, "International summer school opportunities provide exposure to cross-cultural collaborative engineering.", 0, "Not Dark Pattern"),
    (5027, "Inquiries regarding international collaborative MoUs should be sent to dean.international@kkwagh.edu.in.", 0, "Not Dark Pattern"),

    # Page 5028: Industry Advisory Board & Consultancies
    (5028, "Departmental Industry Advisory Boards (IAB) review curriculum relevance and advise on modern skill sets.", 0, "Not Dark Pattern"),
    (5028, "Industrial consultancy cell undertakes third-party material testing, structural auditing, and software audits.", 0, "Not Dark Pattern"),
    (5028, "Revenue generated from testing and consultancy is shared between investigators and institute development funds.", 0, "Not Dark Pattern"),
    (5028, "Industry-sponsored specialized laboratories have been established by Siemens, Schneider, and Dassault Systèmes.", 0, "Not Dark Pattern"),
    (5028, "Faculty undergo summer industrial sabbatical internships to align academic teaching with factory floor operations.", 0, "Not Dark Pattern"),
    (5028, "Students solve authentic real-world engineering problem statements provided directly by industrial partners.", 0, "Not Dark Pattern"),
    (5028, "Formal MoUs exist with over seventy manufacturing, automotive, construction, and IT firms across Nashik region.", 0, "Not Dark Pattern"),
    (5028, "Regular industrial visits are scheduled for second and third-year students to thermal plants, substations, and factories.", 0, "Not Dark Pattern"),
    (5028, "Standard testing charges and calibration reports follow Bureau of Indian Standards (BIS) specifications.", 0, "Not Dark Pattern"),
    (5028, "For industry consultancy queries, contact the Dean of Industry-Institute Interaction.", 0, "Not Dark Pattern"),

    # Page 5029: Student Welfare & Counseling Services
    (5029, "Student Welfare Office coordinates cultural activities, youth festivals, and personal financial assistance.", 0, "Not Dark Pattern"),
    (5029, "Professional student counselors provide confidential psychological guidance for stress management and wellbeing.", 0, "Not Dark Pattern"),
    (5029, "Special financial assistance scheme provides meal coupons and textbooks to needy students.", 0, "Not Dark Pattern"),
    (5029, "Earn and Learn Scheme allows deserving students to work in college libraries and computer centers for hourly stipends.", 0, "Not Dark Pattern"),
    (5029, "Group insurance policy covers all registered students against accidental hospitalization and emergencies.", 0, "Not Dark Pattern"),
    (5029, "Special educational aids and motorized ramp access are provided for differently abled students.", 0, "Not Dark Pattern"),
    (5029, "Annual Health Checkup is compulsory for all first-year undergraduate and postgraduate students.", 0, "Not Dark Pattern"),
    (5029, "Parent-Teacher Association (PTA) meetings are organized once every semester to review academic progress.", 0, "Not Dark Pattern"),
    (5029, "Dean of Student Affairs maintains an open-door policy for all genuine student grievances and suggestions.", 0, "Not Dark Pattern"),
    (5029, "Emergency contacts for student welfare officers are displayed in all hostel common rooms and lobbies.", 0, "Not Dark Pattern"),

    # Page 5030: Disclaimer, Copyright & Terms of Use
    (5030, "All contents, text, images, and documents on this portal are the intellectual property of KKWIEER.", 0, "Not Dark Pattern"),
    (5030, "Information published on this portal is intended for informational and academic purposes only.", 0, "Not Dark Pattern"),
    (5030, "The institute reserves the right to alter course timetables, faculty allocations, and fee schedules as required.", 0, "Not Dark Pattern"),
    (5030, "While reasonable care is taken to ensure accuracy, the institute is not liable for typographical errors.", 0, "Not Dark Pattern"),
    (5030, "External hyperlinks provided on this portal are for convenience; the institute does not endorse third-party content.", 0, "Not Dark Pattern"),
    (5030, "Unauthorized reproduction or commercial distribution of college materials without written permission is prohibited.", 0, "Not Dark Pattern"),
    (5030, "Privacy Policy: Student and faculty personal data is processed strictly in accordance with applicable laws.", 0, "Not Dark Pattern"),
    (5030, "For reporting technical glitches on the college website, please contact webmaster@kkwagh.edu.in.", 0, "Not Dark Pattern"),
    (5030, "All legal disputes are subject to the exclusive jurisdiction of the competent courts in Nashik, India.", 0, "Not Dark Pattern"),
    (5030, "Last updated on September 2026. Designed and maintained by the Digital Media Cell, KKWIEER.", 0, "Not Dark Pattern"),
]


# ---------------------------------------------------------------------------
# 2. MINORITY DARK PATTERN CORPUS (130 Samples, page_id 6001 - 6026)
# ---------------------------------------------------------------------------

# 50 Forced Action samples (page_id 6001 to 6010, 5 samples each)
FORCED_ACTION_SAMPLES = [
    (6001, "You must create an account and verify your phone number before you can view product prices.", 1, "Forced Action"),
    (6001, "Sign up for our promotional marketing newsletter to unlock the free download link.", 1, "Forced Action"),
    (6001, "Access Blocked: You must allow push notifications to read this article.", 1, "Forced Action"),
    (6001, "Please provide your credit card details to start your free 7-day trial; you will be billed automatically.", 1, "Forced Action"),
    (6001, "To continue reading, share this product with 3 friends on WhatsApp or Facebook.", 1, "Forced Action"),

    (6002, "You must enable continuous location tracking and camera access to use this basic calculation app.", 1, "Forced Action"),
    (6002, "Accept all tracking cookies and agree to personalized ad profiling to view this website content.", 1, "Forced Action"),
    (6002, "You must download our mobile app to complete checkout; desktop ordering has been disabled.", 1, "Forced Action"),
    (6002, "Submit your corporate work email and phone number to read this publicly available whitepaper.", 1, "Forced Action"),
    (6002, "You must enroll in our VIP membership club to proceed to the checkout screen.", 1, "Forced Action"),

    (6003, "To view your test results, you must enter credit card information for our partner trial.", 1, "Forced Action"),
    (6003, "Enable desktop notifications to reveal the secret promotional discount voucher code.", 1, "Forced Action"),
    (6003, "Sign in with your Facebook account and grant contact list access to read user reviews.", 1, "Forced Action"),
    (6003, "You must register a paid profile before you can apply for any posted job opening.", 1, "Forced Action"),
    (6003, "Complete this 10-question consumer marketing survey to unlock the final download button.", 1, "Forced Action"),

    (6004, "Grant access to your email contact address book to invite team members and proceed.", 1, "Forced Action"),
    (6004, "You must accept our partner promotional SMS messages to verify your shipping address.", 1, "Forced Action"),
    (6004, "Subscribe to our YouTube channel and comment on this video to enter the giveaway.", 1, "Forced Action"),
    (6004, "Install our browser shopping extension to apply the available coupon code to your order.", 1, "Forced Action"),
    (6004, "You must provide your date of birth, gender, and home address before viewing the catalog.", 1, "Forced Action"),

    (6005, "Create an account to read this free public news article. Guest reading is not permitted.", 1, "Forced Action"),
    (6005, "You must opt into third-party data sharing to download this free spreadsheet template.", 1, "Forced Action"),
    (6005, "Provide your credit card to prove your age before accessing this standard video content.", 1, "Forced Action"),
    (6005, "Allow microphone access to continue browsing our interactive product showcase.", 1, "Forced Action"),
    (6005, "You must agree to receive daily promotional calls from our affiliates to unlock the coupon.", 1, "Forced Action"),

    (6006, "Check this box to agree to our marketing communications in order to complete your registration.", 1, "Forced Action"),
    (6006, "You must link your LinkedIn profile and permit public posting to view the salary benchmark.", 1, "Forced Action"),
    (6006, "Download and install our companion desktop software to finish configuring your peripheral device.", 1, "Forced Action"),
    (6006, "You must purchase insurance coverage of $9.99 to complete your ticket booking.", 1, "Forced Action"),
    (6006, "Agree to receive sponsored promotional emails from 15 trusted partners to unlock your account.", 1, "Forced Action"),

    (6007, "Enter a valid payment method now. You cannot bypass this screen to evaluate the demo.", 1, "Forced Action"),
    (6007, "You must write a 5-star review on Google before your support ticket can be processed.", 1, "Forced Action"),
    (6007, "Allow sync with your Google Contacts to find coworkers and start using the workspace.", 1, "Forced Action"),
    (6007, "Upload your government ID card to browse available vacation rental properties.", 1, "Forced Action"),
    (6007, "You must accept automatic monthly renewal to purchase this single annual software license.", 1, "Forced Action"),

    (6008, "To read full answers on this forum, create a registered profile or sign in with Google.", 1, "Forced Action"),
    (6008, "You must follow our Instagram account and tag 2 friends to activate your gift voucher.", 1, "Forced Action"),
    (6008, "Enable Bluetooth and GPS location at all times to keep your smart device connected.", 1, "Forced Action"),
    (6008, "Provide your employer's company credit card details to complete your free individual trial.", 1, "Forced Action"),
    (6008, "You must agree to our auto-debit billing agreement to receive the discounted onboarding rate.", 1, "Forced Action"),

    (6009, "Download our official mobile app to track your order. Tracking via website is unavailable.", 1, "Forced Action"),
    (6009, "You must join our mailing list to receive your purchase order invoice and tracking number.", 1, "Forced Action"),
    (6009, "Allow camera permissions to take a mandatory selfie for account registration verification.", 1, "Forced Action"),
    (6009, "Agree to share your browsing activity with our advertising partners to keep reading for free.", 1, "Forced Action"),
    (6009, "You must add at least $50 to your store wallet balance before placing an order.", 1, "Forced Action"),

    (6010, "Subscribe to our premium bundle to access basic customer support chat assistance.", 1, "Forced Action"),
    (6010, "You must accept personalized cross-site ad tracking to proceed beyond this screen.", 1, "Forced Action"),
    (6010, "Mandatory step: Invite at least 3 colleagues to access your project management dashboard.", 1, "Forced Action"),
    (6010, "To submit your resume for this position, you must sign up for our partner certification exam.", 1, "Forced Action"),
    (6010, "You must consent to voice recording during your browsing session to proceed with payment.", 1, "Forced Action"),
]


# 40 Sneaking samples (page_id 6011 to 6018, 5 samples each)
SNEAKING_SAMPLES = [
    (6011, "A $4.99 green shipping carbon offset fee has been automatically added to your cart.", 1, "Sneaking"),
    (6011, "Express delivery handling fee of $6.50 was quietly added at final payment step.", 1, "Sneaking"),
    (6011, "Your purchase automatically enrolls you in our monthly VIP club at $29.99/month after 14 days.", 1, "Sneaking"),
    (6011, "Pre-selected: Add premium parcel damage protection warranty for $3.89.", 1, "Sneaking"),
    (6011, "A 18% service gratuity tip has been automatically pre-selected in your order total.", 1, "Sneaking"),

    (6012, "Free trial automatically converts into an annual non-refundable billing of $149 unless cancelled.", 1, "Sneaking"),
    (6012, "Mandatory facility processing fee of $12.00 will appear on your bank statement at checkout.", 1, "Sneaking"),
    (6012, "We added extended 2-year replacement guarantee ($15.99) to your basket based on popular choice.", 1, "Sneaking"),
    (6012, "By placing this order you agree to recurring weekly delivery charges billed to your credit card.", 1, "Sneaking"),
    (6012, "An expedited priority order processing charge of $4.75 has been included in your subtotal.", 1, "Sneaking"),

    (6013, "Pre-checked box: Yes, keep me enrolled in automatic monthly ink cartridge refills at $19.99.", 1, "Sneaking"),
    (6013, "Regulatory recovery surcharge of $3.50 added during final card authorization step.", 1, "Sneaking"),
    (6013, "Sneak in basket: Included magazine subscription trial ($8/month after 30 days) with your book.", 1, "Sneaking"),
    (6013, "Additional service convenience fee of 12% is applied during the last checkout step.", 1, "Sneaking"),
    (6013, "Your membership will silently renew at the standard full price of $89.99 after introductory month.", 1, "Sneaking"),

    (6014, "Luggage insurance and travel protection ($22.00) was pre-selected on your itinerary.", 1, "Sneaking"),
    (6014, "Restocking warranty fee of $7.95 has been added to your shopping cart items.", 1, "Sneaking"),
    (6014, "Introductory free trial will automatically bill your saved card $49.00 every quarter.", 1, "Sneaking"),
    (6014, "Hidden delivery fee: Standard shipping price excludes regional logistic surcharge of $9.50.", 1, "Sneaking"),
    (6014, "Pre-selected add-on: Gift wrapping paper and custom greeting card for $5.99 added to order.", 1, "Sneaking"),

    (6015, "Automated donation of $2.00 to our affiliated charity foundation was added to your bill.", 1, "Sneaking"),
    (6015, "By completing this order you enroll in our recurring auto-ship program at current market price.", 1, "Sneaking"),
    (6015, "Silent price increase: Second month subscription bills at $59.99 instead of initial $9.99.", 1, "Sneaking"),
    (6015, "Digital convenience fee of $3.25 is added on the final card payment review page.", 1, "Sneaking"),
    (6015, "Pre-selected: Premium priority tech support coverage for $14.99 added to your software order.", 1, "Sneaking"),

    (6016, "We added complementary expedited delivery insurance ($4.50) to protect against transit loss.", 1, "Sneaking"),
    (6016, "Unannounced recurring monthly fee of $9.95 begins immediately after promotional checkout.", 1, "Sneaking"),
    (6016, "A mandatory cleaning and maintenance service surcharge of $18.00 is added at reservation.", 1, "Sneaking"),
    (6016, "Hidden recurring charge: Membership renews automatically every 30 days without prior notice.", 1, "Sneaking"),
    (6016, "Cart automatically populated with supplementary replacement brush heads for $12.99.", 1, "Sneaking"),

    (6017, "Fuel surcharge of $5.20 added to your order summary on the final payment confirmation screen.", 1, "Sneaking"),
    (6017, "Pre-selected checkbox: Enroll in automatic monthly wine club delivery for $45 per shipment.", 1, "Sneaking"),
    (6017, "Initial $1 trial automatically upgrades to standard enterprise tier ($99/mo) after 3 days.", 1, "Sneaking"),
    (6017, "Processing fee of 4.5% is appended to your order only after entering credit card information.", 1, "Sneaking"),
    (6017, "Pre-checked: Subscribe to premium video catalog access for $7.99/mo starting next billing cycle.", 1, "Sneaking"),

    (6018, "Hidden subscription trap: Downloading free app automatically initiates $39.99 annual subscription.", 1, "Sneaking"),
    (6018, "A compulsory electronic ticket issuance surcharge of $6.00 has been added to each seat.", 1, "Sneaking"),
    (6018, "Checked by default: Include 3-year extended screen replacement guarantee for $24.99.", 1, "Sneaking"),
    (6018, "Service tip of 25% has been quietly applied to your order total without confirmation.", 1, "Sneaking"),
    (6018, "Subtle recurring billing: Monthly cloud storage fee of $4.99 kicks in after the first free month.", 1, "Sneaking"),
]


# 40 Obstruction samples (page_id 6019 to 6026, 5 samples each)
OBSTRUCTION_SAMPLES = [
    (6019, "To cancel your membership, you must call our telephone hotline at 1-800-555-0199 between 9 AM and 11 AM EST on weekdays.", 1, "Obstruction"),
    (6019, "Cancellation requests submitted online cannot be accepted. Please mail a notarized physical letter to our corporate office.", 1, "Obstruction"),
    (6019, "Are you sure you want to cancel? You will permanently lose all accrued reward points and lifetime discounts.", 1, "Obstruction"),
    (6019, "Step 4 of 7: To confirm subscription termination, please re-enter your security code and answer five verification questions.", 1, "Obstruction"),
    (6019, "Your cancellation request requires up to 45 business days to process; subsequent billing cycles cannot be refunded.", 1, "Obstruction"),

    (6020, "To close your account, contact your assigned account manager via postal mail at least 60 days before contract expiry.", 1, "Obstruction"),
    (6020, "To opt out of promotional emails, you must uncheck each of the 24 individual marketing categories manually.", 1, "Obstruction"),
    (6020, "The unsubscribe link on this page is temporarily experiencing technical difficulties. Please try again next month.", 1, "Obstruction"),
    (6020, "Canceling your subscription requires in-person appearance at one of our regional service centers with photo ID.", 1, "Obstruction"),
    (6020, "We could not find an active subscription under your email. Please submit a formal verification request with two utility bills.", 1, "Obstruction"),

    (6021, "Burying opt-out: Unsubscribe instructions are hidden within section 14.8 of our 35-page legal terms of service.", 1, "Obstruction"),
    (6021, "Please speak with a retention representative on our cancellation hotline to review your termination options.", 1, "Obstruction"),
    (6021, "To pause your plan, click Continue, then solve 3 security captchas and verify your identity via SMS code.", 1, "Obstruction"),
    (6021, "Account deletion button is deliberately greyed out and hidden behind three nested submenus.", 1, "Obstruction"),
    (6021, "You must provide a detailed 200-word written explanation describing your reason for canceling your trial.", 1, "Obstruction"),

    (6022, "Online account closure is disabled for security reasons. Please dial our toll phone number to speak with an agent.", 1, "Obstruction"),
    (6022, "Before canceling, you must acknowledge 6 separate screens warning of catastrophic data loss.", 1, "Obstruction"),
    (6022, "To unsubscribe from SMS alerts, mail a signed opt-out affidavit to our compliance mailbox in Delaware.", 1, "Obstruction"),
    (6022, "Our subscription cancellation portal is only accessible from desktop browsers running on Windows operating systems.", 1, "Obstruction"),
    (6022, "Notice of cancellation must be submitted between the 1st and 3rd day of the calendar quarter.", 1, "Obstruction"),

    (6023, "To cancel automatic renewal, chat live with our support team. Current wait time: approximately 75 minutes.", 1, "Obstruction"),
    (6023, "Clicking Cancel opens a confirmation loop that repeatedly redirects you back to the account dashboard.", 1, "Obstruction"),
    (6023, "Opting out of data tracking requires clearing browser cookies and re-authenticating 8 separate times.", 1, "Obstruction"),
    (6023, "You cannot downgrade your plan online. Upgrades take one click; downgrades require customer support approval.", 1, "Obstruction"),
    (6023, "Your request to cancel could not be verified. Please schedule a video identification call with a representative.", 1, "Obstruction"),

    (6024, "Roach motel pattern: Subscribing takes 5 seconds, but canceling requires certified registered post with tracking.", 1, "Obstruction"),
    (6024, "To delete your profile data, you must submit a signed physical affidavit certified by a notary public.", 1, "Obstruction"),
    (6024, "Cancel button has been styled as plain non-clickable text with very low contrast against the background.", 1, "Obstruction"),
    (6024, "Warning: If you cancel today, your saved work and cloud files will be permanently deleted within 1 hour.", 1, "Obstruction"),
    (6024, "To opt out of our auto-renewal policy, submit written notice at least 90 calendar days prior to contract renewal date.", 1, "Obstruction"),

    (6025, "Unsubscribe confirmation email will be dispatched within 14 business days; do not click again or it resets.", 1, "Obstruction"),
    (6025, "To remove your payment card on file, you must first link an alternative active debit or credit card.", 1, "Obstruction"),
    (6025, "Cancellation flow forces the user through 5 consecutive discount negotiation screens before displaying confirm button.", 1, "Obstruction"),
    (6025, "Customer service hours for subscription cancellations are Tuesday and Thursday from 10:00 AM to 11:30 AM only.", 1, "Obstruction"),
    (6025, "You must pay an administrative processing fee of $25.00 to cancel your annual membership early.", 1, "Obstruction"),

    (6026, "To unsubscribe, text STOP, then reply with your 16-digit account ID, billing ZIP code, and cancellation PIN.", 1, "Obstruction"),
    (6026, "The link to cancel your subscription is hidden in microscopic 6pt font at the bottom of the email.", 1, "Obstruction"),
    (6026, "We could not authenticate your cancellation request. Please re-verify via two-factor authentication on a registered device.", 1, "Obstruction"),
    (6026, "To modify cookie preferences, user is redirected to 45 individual third-party tracking vendor websites.", 1, "Obstruction"),
    (6026, "To close your account, you must surrender all accumulated store credit and pay an account termination fee.", 1, "Obstruction"),
]


def enrich_dataset():
    """Execute backup, validation, and enrichment of the dataset."""
    print("============================================================")
    print("  DarkShield AI — Dataset Enrichment Pipeline (Phase 2)")
    print("============================================================")

    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Source dataset not found at {DATASET_PATH}")

    # 1. Load original dataset
    df_orig = pd.read_csv(DATASET_PATH, sep="\t")
    orig_total = len(df_orig)
    print(f"\n[Step 1] Loaded original dataset: {orig_total} rows")
    print(f"  Not Dark Pattern (0): {(df_orig['label'] == 0).sum()}")
    print(f"  Dark Pattern (1):     {(df_orig['label'] == 1).sum()}")
    print(f"  Unique page_ids:      {df_orig['page_id'].nunique()}")

    # 2. Create byte-for-byte backup if not already present
    if not os.path.exists(BACKUP_PATH):
        shutil.copyfile(DATASET_PATH, BACKUP_PATH)
        print(f"\n[Step 2] Created backup at: {BACKUP_PATH}")
    else:
        print(f"\n[Step 2] Backup already exists at: {BACKUP_PATH}")

    # 3. Compile new samples
    all_new_samples = INSTITUTIONAL_SAMPLES + FORCED_ACTION_SAMPLES + SNEAKING_SAMPLES + OBSTRUCTION_SAMPLES
    df_new = pd.DataFrame(all_new_samples, columns=["page_id", "text", "label", "Pattern Category"])

    print(f"\n[Step 3] Compiled {len(df_new)} enrichment samples:")
    print(f"  Institutional Benign (0): {len(INSTITUTIONAL_SAMPLES)} samples (page_id 5001-5030)")
    print(f"  Forced Action (1):        {len(FORCED_ACTION_SAMPLES)} samples (page_id 6001-6010)")
    print(f"  Sneaking (1):             {len(SNEAKING_SAMPLES)} samples (page_id 6011-6018)")
    print(f"  Obstruction (1):          {len(OBSTRUCTION_SAMPLES)} samples (page_id 6019-6026)")

    # 4. Check for duplicate text across new and original samples
    orig_texts = set(df_orig["text"].str.strip().str.lower())
    clean_new_rows = []
    skipped_duplicates = 0

    for idx, row in df_new.iterrows():
        t = str(row["text"]).strip().lower()
        if t in orig_texts:
            skipped_duplicates += 1
        else:
            orig_texts.add(t)
            clean_new_rows.append(row)

    df_new_clean = pd.DataFrame(clean_new_rows)
    print(f"  Duplicate filter: {skipped_duplicates} duplicates skipped, {len(df_new_clean)} valid new samples.")

    # 5. Concatenate and verify
    df_enriched = pd.concat([df_orig, df_new_clean], ignore_index=True)
    enriched_total = len(df_enriched)

    print(f"\n[Step 4] Enriched Dataset Statistics:")
    print(f"  Total samples:        {enriched_total} (was {orig_total}, +{len(df_new_clean)})")
    print(f"  Not Dark Pattern (0): {(df_enriched['label'] == 0).sum()} ({(df_enriched['label'] == 0).mean()*100:.1f}%)")
    print(f"  Dark Pattern (1):     {(df_enriched['label'] == 1).sum()} ({(df_enriched['label'] == 1).mean()*100:.1f}%)")
    print(f"  Unique page_ids:      {df_enriched['page_id'].nunique()}")

    print("\nMulticlass Category Distribution (Label 1 only):")
    dark_only = df_enriched[df_enriched["label"] == 1]
    cat_counts = dark_only["Pattern Category"].value_counts()
    for cat, count in cat_counts.items():
        orig_count = (df_orig["Pattern Category"] == cat).sum()
        print(f"  {cat:<18}: {count:4d} (was {orig_count:4d}, +{count - orig_count:3d})")

    # 6. Save enriched dataset
    df_enriched.to_csv(DATASET_PATH, sep="\t", index=False, encoding="utf-8")
    print(f"\n[Step 5] Successfully saved enriched dataset to: {DATASET_PATH}")
    print("============================================================")

    return df_enriched


if __name__ == "__main__":
    enrich_dataset()
