from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime


def wrap_text(text, max_chars=95):
    words = str(text).split()
    lines = []
    line = ""

    for word in words:
        if len(line + word) < max_chars:
            line += word + " "
        else:
            lines.append(line.strip())
            line = word + " "

    if line:
        lines.append(line.strip())

    return lines


def generate_pdf_report(report, role, difficulty, interview_type, total_questions):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    overall_score = report.get("overall_score", 0)
    verdict = report.get("verdict", "Unknown")
    summary_feedback = report.get("summary_feedback", "")
    improvement_plan = report.get("improvement_plan", "")
    question_wise = report.get("question_wise", [])

    # ---------------- HEADER ----------------
    c.setFillColor(colors.darkblue)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "AI Interview Report (MAANG Style)")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    c.line(50, height - 80, width - 50, height - 80)

    y = height - 110

    # ---------------- SETTINGS ----------------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Interview Settings")
    y -= 20

    c.setFont("Helvetica", 11)
    c.drawString(60, y, f"Role: {role}")
    y -= 15
    c.drawString(60, y, f"Difficulty: {difficulty}")
    y -= 15
    c.drawString(60, y, f"Interview Type: {interview_type}")
    y -= 15
    c.drawString(60, y, f"Total Questions: {total_questions}")
    y -= 25

    # ---------------- SUMMARY ----------------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Final Result")
    y -= 20

    c.setFont("Helvetica", 11)
    c.drawString(60, y, f"Overall Score: {overall_score} / 10")
    y -= 15

    # Verdict color
    if "Strong" in verdict:
        c.setFillColor(colors.green)
    elif "Hire" in verdict:
        c.setFillColor(colors.darkgreen)
    elif "Maybe" in verdict:
        c.setFillColor(colors.orange)
    else:
        c.setFillColor(colors.red)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, f"Verdict: {verdict}")

    c.setFillColor(colors.black)
    y -= 30

    # ---------------- SUMMARY FEEDBACK ----------------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Summary Feedback")
    y -= 20

    c.setFont("Helvetica", 10)
    for line in wrap_text(summary_feedback, 95):
        c.drawString(60, y, line)
        y -= 12
        if y < 80:
            c.showPage()
            y = height - 60

    y -= 15

    # ---------------- IMPROVEMENT PLAN ----------------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Improvement Plan")
    y -= 20

    c.setFont("Helvetica", 10)
    for line in wrap_text(improvement_plan, 95):
        c.drawString(60, y, line)
        y -= 12
        if y < 80:
            c.showPage()
            y = height - 60

    y -= 20

    # ---------------- QUESTION WISE EVALUATION ----------------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Question Wise Evaluation")
    y -= 25

    for i, item in enumerate(question_wise, start=1):

        if y < 200:
            c.showPage()
            y = height - 60

        question = item.get("question", "")
        candidate_answer = item.get("candidate_answer", "")
        score = item.get("score", 0)
        feedback = item.get("feedback", "")
        improvement = item.get("improvement", "")
        ideal_answer = item.get("ideal_answer", "")

        c.setFillColor(colors.darkblue)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, f"Q{i}: {question[:80]}")
        c.setFillColor(colors.black)
        y -= 18

        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y, f"Score: {score} / 10")
        y -= 15

        # Candidate Answer
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y, "Candidate Answer:")
        y -= 12

        c.setFont("Helvetica", 9)
        for line in wrap_text(candidate_answer, 95):
            c.drawString(70, y, line)
            y -= 11
            if y < 80:
                c.showPage()
                y = height - 60

        y -= 10

        # Feedback
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y, "Feedback:")
        y -= 12

        c.setFont("Helvetica", 9)
        for line in wrap_text(feedback, 95):
            c.drawString(70, y, line)
            y -= 11
            if y < 80:
                c.showPage()
                y = height - 60

        y -= 10

        # Improvement
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y, "Improvement:")
        y -= 12

        c.setFont("Helvetica", 9)
        for line in wrap_text(improvement, 95):
            c.drawString(70, y, line)
            y -= 11
            if y < 80:
                c.showPage()
                y = height - 60

        y -= 10

        # Ideal Answer
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y, "Ideal Answer (MAANG Standard):")
        y -= 12

        c.setFont("Helvetica", 9)
        for line in wrap_text(ideal_answer, 95):
            c.drawString(70, y, line)
            y -= 11
            if y < 80:
                c.showPage()
                y = height - 60

        y -= 25

    c.save()
    buffer.seek(0)
    return buffer
