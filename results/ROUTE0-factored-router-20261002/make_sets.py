"""Fresh evaluation sets for the ROUTE0 request router.

Deterministic (seeded). Writes sets.json next to this file:
    {"A3": [[text, truth], ...], ...}   truth in {"email-full", "desk-commitment", "out"}

Written blind to the router's code, tests and earlier sets. The only things read
from the repository are the two members' training corpora (A3 draws its pools
from them; every other set asserts it does NOT reuse their senders, subjects or
previews) and the OpenClaw wrapping regexes, copied verbatim below.

Run:  python3 results/ROUTE0-factored-router-20261002/make_sets.py
"""
import datetime
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SEED = 20261002

EF, DK, OUT = "email-full", "desk-commitment", "out"
MEMBERS = (EF, DK)
TASK = {EF: "Is this important?", DK: "What date did you commit to in this thread?"}
CORPUS = {EF: REPO / "training/harness/data_ef/train.jsonl",
          DK: REPO / "training/harness/data_desk/train.jsonl"}
TOOL_CUT = "\n\nThe following tools are available"

# Copied verbatim from examples/school/gateway.py (used only to verify H3 unwraps).
_RUNTIME_CONTEXT = re.compile(r"<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>.*?<<<END_OPENCLAW_INTERNAL_CONTEXT>>>", re.S)
_STAMP = re.compile(r"^\[[A-Z][a-z]{2} \d{4}-\d{2}-\d{2} \d{2}:\d{2}[^\]]*\]\s*")
_RUNTIME_FOOTER = re.compile(r"\n+Runtime: agent=.*\Z", re.S)

EST_LINES = ["  You made a promise in this thread: yes",
             "  The promise is yours, not the sender's: yes",
             "  It is in the last message you wrote: yes"]


# --------------------------------------------------------------------------- corpus pools (A3 only)
AUTO_PREVIEW = "This is an automated message."


def corpus_pools(member):
    """Sender/subject/preview pools, kept per category (automated vs person) so A3
    respects the corpus's joint shape: automated senders carry automated subjects
    and the automated preview; people carry person subjects and previews."""
    cats = {}
    ids = set()
    for line in CORPUS[member].read_text().splitlines():
        row = json.loads(line)
        user = next(m["content"] for m in row["messages"] if m["role"] == "user")
        req = user.split(TOOL_CUT)[0]
        f = re.search(r"^From: (.*)$", req, re.M).group(1)
        s = re.search(r"^Subject: (.*)$", req, re.M).group(1)
        p = re.search(r"^Preview: (.*)$", req, re.M).group(1)
        ids.add(int(re.search(r"msg-(\d+)", req).group(1)))
        c = cats.setdefault(p == AUTO_PREVIEW, (set(), set(), set()))
        c[0].add(f); c[1].add(s); c[2].add(p)
    cats = {k: tuple(sorted(x) for x in v) for k, v in cats.items()}
    froms = sorted(set().union(*(set(v[0]) for v in cats.values())))
    subjs = sorted(set().union(*(set(v[1]) for v in cats.values())))
    prevs = sorted(set().union(*(set(v[2]) for v in cats.values())))
    return froms, subjs, prevs, ids, cats


POOLS = {m: corpus_pools(m) for m in MEMBERS}


# --------------------------------------------------------------------------- fresh material (written for this set)
PEOPLE = [
    ("Aroha Ngata", "aroha.ngata@waikatoregional.govt.nz"),
    ("Tamati Walker", "tamati@kiwiorchard.co.nz"),
    ("Siobhan O'Connell", "s.oconnell@harbourlane.co.uk"),
    ("Rupert Ashdown-Blake", "rupert.ashdown-blake@fenwickpartners.co.uk"),
    ("Jürgen Faßbender", "j.fassbender@kraemer-logistik.de"),
    ("Annika Schröder", "annika.schroeder@stadtwerke-ulm.de"),
    ("Mathilde Lefèvre", "mathilde.lefevre@atelier-brume.fr"),
    ("Søren Kjærgaard", "sk@nordhavn-design.dk"),
    ("Ingrid Halvorsen", "ingrid.halvorsen@fjordkraft-energi.no"),
    ("Eeva Mäkinen", "eeva.makinen@sauna-labs.fi"),
    ("Wojciech Nowakowski", "w.nowakowski@vistula-soft.pl"),
    ("Zuzana Horváthová", "zuzana.horvathova@tatrabuild.sk"),
    ("Giulia Bernasconi", "g.bernasconi@studiolegale-bernasconi.it"),
    ("Íñigo Etxeberria", "inigo.etxeberria@bilbaoport.eus"),
    ("Mariana Gonçalves", "mariana.goncalves@lisboaventures.pt"),
    ("Thiago Albuquerque", "thiago.albuquerque@cafe-serra.com.br"),
    ("Valentina Restrepo", "vrestrepo@medellin-agro.co"),
    ("Camila Fuenzalida", "camila.fuenzalida@andesmining.cl"),
    ("Hiroshi Tanaka", "h.tanaka@kansai-precision.co.jp"),
    ("Mei-Ling Chou", "meiling.chou@tamsui-semis.com.tw"),
    ("Ji-woo Park", "jiwoo.park@hanriver-bio.kr"),
    ("Arjun Venkataraman", "arjun.v@bluepeak.io"),
    ("Priya Raghunathan", "priya@tiffinbox.in"),
    ("Nguyen Thi Lan", "lan.nguyen@mekongfreight.vn"),
    ("Kwame Mensah", "kwame.mensah@accra-solar.com.gh"),
    ("Chiamaka Okafor", "chiamaka.okafor@lagosledger.ng"),
    ("Thandiwe Dlamini", "thandiwe@capetide.co.za"),
    ("Youssef El Amrani", "youssef.elamrani@atlas-textiles.ma"),
    ("Leyla Demir", "leyla.demir@bosphorus-analytics.com.tr"),
    ("Noa Ben-David", "noa@carmel-robotics.co.il"),
    ("Olena Shevchenko", "olena.shevchenko@dnipro-studio.com.ua"),
    ("Callum MacLeod", "callum.macleod@hebrides-trust.org"),
    ("Bridget Nakamura-Hayes", "bridget.nh@gmail.com"),
    ("Dmitri Volkov", "dvolkov.consulting@gmail.com"),
    ("Hannah Whitcombe", "hannah@whitcombe-ceramics.com.au"),
    ("Jack Thornbury", "jack.thornbury@outlook.com"),
    ("Fatima Zahra Benali", "fz.benali@medecins-solidaires.org"),
    ("Pieter van der Berg", "pieter.vandenberg@deltawater.nl"),
    ("Elodie Vanderstraeten", "elodie@brusselsbikes.be"),
    ("Marcus Lindqvist", "marcus.lindqvist@vasteras-motor.se"),
    ("Rafael Domínguez", "rdominguez@monterrey-steel.com.mx"),
    ("Sakura Ishikawa", "sakura@fernleaf.io"),
    ("Óscar Ruiz-Tagle", "oscar@quilmes-coop.org.ar"),
    ("Grace Kariuki", "grace.kariuki@nairobi-health.or.ke"),
    ("Tomás Ó Briain", "tomas.obriain@gaillimh-tech.ie"),
    ("Lucía Paredes", "lucia.paredes@cuzco-tours.pe"),
]
AUTOMATED = [
    ("Xero", "messaging-service@post.xero.com"),
    ("GitHub", "noreply@github.com"),
    ("Jira Cloud", "jira@ferncroft.atlassian.net"),
    ("Deutsche Bahn", "buchungsbestaetigung@bahn.de"),
    ("Stripe", "receipts@stripe.com"),
    ("Google Calendar", "calendar-notification@google.com"),
    ("Notion Team", "notify@mail.notion.so"),
    ("NZ Post", "tracking@nzpost.co.nz"),
    ("HMRC", "no-reply@notifications.hmrc.gov.uk"),
    ("Slack", "feedback@slack.com"),
    ("Mailchimp", "updates@mailchimp-ops.io"),
    ("Linear", "notifications@linear.app"),
    ("Airtable", "no-reply@airtable.com"),
    ("DocuSign", "dse@docusign.net"),
    ("Sentry", "alerts@sentry.io"),
]
EF_SUBJECTS = [
    "Fwd: revised Q4 forecast — please sanity-check before Monday",
    "Re: Re: Wellington site visit (hotel + rental car)",
    "Can you sign off the supplier onboarding form today?",
    "Fwd: Rechnung Nr. 2026-0918 / Bitte um Freigabe",
    "Draft board minutes for your review",
    "[ACTION REQUIRED] Renew your TLS certificate for api.bluepeak.io",
    "Lunch next Thursday?",
    "Re: Proposal v3 — comments inline, mostly typos",
    "Your order #A-77213 has shipped",
    "Re: pricing for the Lisbon pilot (EUR vs USD?)",
    "Changes to our privacy policy",
    "Quick favour: intro to someone at the port authority",
    "Fwd: Fwd: candidate shortlist — product designer role",
    "Re: Kick-off agenda for the Accra rollout, 14 Oct",
    "Weekly digest: 12 new posts in #platform",
    "Overdue: timesheet for week 39",
    "Re: Vertrag — Anpassung §4 Haftung",
    "Invitation: Quarterly business review @ Tue 21 Oct 15:00 (NZDT)",
    "Re: the ferry schedule changed again!!",
    "Thank you for your donation",
    "Re: Can we move our 1:1? Something came up",
    "Pull request #482 was merged",
    "Fwd: Audit findings — section 3 needs a response by Friday",
    "Re: Shipment held at customs (Durban) — documents missing?",
    "Your September statement is ready",
    "Re: Re: Re: pilot results, final numbers attached",
    "Conference speaker confirmation — Kraków, 6–7 Nov",
    "Re: quick question about the API rate limits",
    "Reminder: office closed on Monday (public holiday)",
    "Re: Feedback on the onboarding deck (slides 4–9)",
    "Fwd: tenancy renewal — landlord wants an answer this week",
    "Re: ¿Podemos cerrar el presupuesto hoy?",
    "Security alert: new sign-in from Chrome on Windows",
    "Re: hiring plan for 2027 — headcount by team",
    "Webinar recording: Scaling cold-chain logistics",
    "Re: your expense claim was returned (missing receipt)",
    "Re: Sauna Labs partnership — next steps?",
    "Shared with you: 'Field survey results Oct 2026.xlsx'",
]
EF_PREVIEWS = [
    "Hi, attaching the updated file — could you have a look before we send it on?",
    "Following up on my email from last week, did you get a chance to review the contract?",
    "Your package is on its way and should arrive Thursday.",
    "This is an automated notification. Please do not reply.",
    "Thanks again for yesterday! As promised, here are the slides.",
    "Kia ora, just checking you're still okay to present at the hui on the 9th.",
    "Hallo, anbei die korrigierte Rechnung. Bitte kurz bestätigen.",
    "We need your approval on the PO before finance can release the payment.",
    "No rush on this, but whenever you have a minute I'd love your thoughts.",
    "Unsubscribe from these emails at any time.",
    "Sorry for the delay — the numbers are below, let me know if anything looks off.",
    "Can you confirm by end of day whether we go with option A or B?",
    "FYI only, no action needed from you.",
    "You were mentioned in a comment: \"@you can you double check this?\"",
    "Looping in Grace, who owns the customer side of this.",
    "Hola, te escribo por lo del presupuesto que quedó pendiente.",
    "Your receipt from Stripe for NZD 49.00.",
    "Just a heads-up that the build failed on main after the last merge.",
    "Would Tuesday or Wednesday work better for you?",
    "I've forwarded this to you because you were on the original thread.",
    "Please find attached the signed copy for your records.",
    "Great catching up — let's pick this up again after the holidays.",
    "Two questions about clause 7, otherwise we're good to sign.",
    "Your monthly summary: 14 tasks completed, 3 overdue.",
    "Bonjour, je reviens vers vous concernant la livraison prévue.",
    "Can you send me the login for the staging server? Mine expired.",
    "Hi team — reminder that timesheets are due today at 5pm.",
    "We noticed a sign-in from a new device. If this was you, you can ignore this.",
]
DK_SUBJECTS = [
    "Re: delivery of the translated manuals",
    "Re: Re: when can we expect the revised quote?",
    "Fwd: client is asking about the go-live date",
    "Re: Board pack — your section",
    "Re: Dachsanierung Termin / roof repair schedule",
    "Re: the grant report (due soon?)",
    "Re: sample shipment to Busan",
    "Re: final invoice + handover documents",
    "Re: Can you get the API docs to us before the audit?",
    "Re: photos from the site visit",
    "Re: Re: Re: Ministry submission — your chapter",
    "Re: payroll file for October",
    "Re: menu tasting & final headcount",
    "Re: firmware build for the field units",
    "Re: Bewerbungsunterlagen / reference letter for Annika",
    "Re: data export for the Cape Town office",
    "Re: Wedding photos — when will the album be ready?",
    "Re: second round of edits on chapter 6",
    "Re: renewal paperwork for the warehouse lease",
    "Re: training slides for the Nairobi cohort",
    "Re: entrega del informe trimestral",
    "Re: test results for batch 17",
    "Re: your review of my pull request",
    "Re: logo files (vector please!)",
    "Re: retainer agreement — signed copy",
    "Re: sample size calc for the Lima survey",
    "Re: the podcast edit — any update?",
    "Re: customs paperwork for the Durban container",
]
DK_PREVIEWS = [
    "Just checking the date you gave us still holds — the client is asking.",
    "Thanks! So we're aligned on the timing you mentioned?",
    "Following up: you said you'd have it to us by early next week, still on track?",
    "Great, I've put that date in our project plan.",
    "Kia ora — can you confirm the date again so I can tell the board?",
    "Perfect, I'll let the team know to expect it then.",
    "Hi, the printer needs the files — is the date you promised firm?",
    "Gracias, ¿sigue en pie la fecha que acordamos?",
    "Danke für die Zusage! Bleibt es bei dem Termin?",
    "We've booked the courier around your date, just so you know.",
    "Any update? You mentioned it would be ready soon.",
    "Noted — I'll block the morning of the date you suggested.",
    "Sorry to chase, but finance needs the delivery date in writing.",
    "Thanks for committing to that, it really helps us plan.",
    "Just making sure nothing has slipped on your side.",
    "Bonjour, la date que vous avez indiquée tient toujours ?",
    "The auditors arrive soon, so your date matters a lot here.",
    "Received, thank you — calendar invite to follow.",
    "Can I tell the customer the date you gave me is final?",
    "Ok, so the plan is still the one from your last email?",
]

_AUTO_HINTS = ("shipped", "privacy policy", "digest", "Overdue", "Invitation:", "donation", "merged",
               "statement", "Webinar", "Security alert", "Shared with you", "ACTION REQUIRED", "Reminder:",
               "expense claim")
EF_AUTO_SUBJECTS = [x for x in EF_SUBJECTS if any(h in x for h in _AUTO_HINTS)]
EF_PERSON_SUBJECTS = [x for x in EF_SUBJECTS if x not in EF_AUTO_SUBJECTS]
_AUTO_PREV_HINTS = ("package", "automated", "Unsubscribe", "mentioned in a comment", "receipt",
                    "build failed", "monthly summary", "sign-in", "timesheets")
EF_AUTO_PREVIEWS = [x for x in EF_PREVIEWS if any(h in x for h in _AUTO_PREV_HINTS)]
EF_PERSON_PREVIEWS = [x for x in EF_PREVIEWS if x not in EF_AUTO_PREVIEWS]

# Tasks the members were not trained for (E3).
OTHER_TASKS = [
    "Draft a polite reply saying I'll get back to them next week.",
    "Summarise this in two sentences.",
    "Translate the subject line into Spanish.",
    "Forward this to my assistant with a short note.",
    "Schedule a 30-minute call with the sender for Thursday afternoon.",
    "Is the sender a person or an automated system?",
    "Extract the sender's email address.",
    "Which company does the sender work for?",
    "Write a one-line out-of-office reply to this.",
    "What language is the preview written in?",
    "Archive this and set a reminder for Monday.",
    "Put this sender on my VIP list.",
    "Turn this into a to-do item with a due date.",
    "Rewrite the subject so it is clearer.",
    "Reply declining, and keep it friendly.",
    "Who should I loop in on this?",
    "Add this sender to my contacts.",
    "Classify this email as sales, support, billing or personal.",
    "Draft a follow-up asking for the attachment they mentioned.",
    "What is the sender's first name?",
    "Mark this as spam and block the sender.",
    "Create a calendar hold based on this message.",
    "Write a short thank-you note in reply.",
    "Is the tone of the preview friendly or annoyed?",
    "Count how many messages are in this thread.",
    "Find every other email from this sender.",
    "Label this as 'Finance' and move it to that folder.",
    "Suggest three possible replies I could send.",
]
# Second instructions appended in their own paragraph (E4).
SECOND_INSTR = [
    "Then draft a reply.",
    "Also tell me who else is cc'd.",
    "After that, forward it to my manager.",
    "And summarise the thread in one line.",
    "Then add a reminder to my calendar.",
    "Also translate the preview into German.",
    "Once you know, write the sender a short answer.",
    "Then archive it.",
    "Also extract any phone numbers in the message.",
    "And list the attachments, if there are any.",
    "Afterwards, move it to the 'Follow up' folder.",
    "Also check whether I've replied to this person before and quote my last message.",
    "Then send a confirmation to the sender.",
    "Also give me the sender's job title.",
    "And then unsubscribe me if it's a newsletter.",
    "Then create a task for it in my to-do list.",
    "Also tell me what time zone the sender is in.",
    "After that, draft a note to the team about it.",
]
PARAPHRASE = {
    EF: [
        "Should I care about this one?",
        "Does this need my attention?",
        "Is this worth my time?",
        "Do I need to deal with this?",
        "Is this one a priority?",
        "Can I safely ignore this email?",
        "Is this message one I should act on?",
        "Would you flag this as important?",
        "How important is this email?",
        "Is this something I have to look at?",
        "Does this one matter?",
        "Important or not?",
        "Should this go to the top of my inbox?",
        "Is this email significant for me?",
        "Must I respond to this, or is it noise?",
        "Is this a message I shouldn't miss?",
        "Do you think this one is important?",
        "Is this high priority?",
        "Should I bother opening this?",
        "Does this deserve attention today?",
    ],
    DK: [
        "When did I promise to deliver?",
        "What deadline did I agree to here?",
        "Which date did I commit to?",
        "What date did I promise in this conversation?",
        "By when did I say I'd have it done?",
        "What delivery date did I give them?",
        "Which day did I promise them?",
        "What date did I agree to in this exchange?",
        "When did I say it would be ready?",
        "What due date did I commit to on this thread?",
        "Remind me what date I promised.",
        "What was the date I committed to?",
        "On what date did I say I'd deliver?",
        "Which deadline did I sign up for in this thread?",
        "What date did I give as my commitment here?",
        "When did I tell them to expect it?",
        "What's the date I promised in this email chain?",
        "Tell me the date I committed to.",
    ],
}


# --------------------------------------------------------------------------- builders
def header(rng, frm, subj, prev, ids=None):
    if ids is None:
        m = rng.randint(100, 9999)
        t = m if rng.random() < 0.5 else rng.randint(100, 9999)
        ids = (f"{m:04d}" if m > 999 else f"{m:03d}", f"{t:04d}" if t > 999 else f"{t:03d}")
    return (f"Message msg-{ids[0]} in thread thr-{ids[1]}\nFrom: {frm}\n"
            f"Subject: {subj}\nPreview: {prev}")


def established(rng):
    k = rng.choice([0, 1, 1, 2, 2, 3, 3])
    if k == 0:
        return ""
    return "\n\nAlready established:\n" + "\n".join(EST_LINES[:k])


def fresh_content(member, rng):
    """F3-like content: header lines (+ desk's established paragraph), no task."""
    if member == EF:
        if rng.random() < 0.3:
            name, addr = rng.choice(AUTOMATED)
            return header(rng, f"{name} <{addr}>", rng.choice(EF_AUTO_SUBJECTS), rng.choice(EF_AUTO_PREVIEWS))
        name, addr = rng.choice(PEOPLE)
        return header(rng, f"{name} <{addr}>", rng.choice(EF_PERSON_SUBJECTS), rng.choice(EF_PERSON_PREVIEWS))
    name, addr = rng.choice(PEOPLE)
    return header(rng, f"{name} <{addr}>", rng.choice(DK_SUBJECTS),
                  rng.choice(DK_PREVIEWS)) + established(rng)


def corpus_content(member, rng):
    used, cats = POOLS[member][3], POOLS[member][4]
    n = rng.choice([i for i in range(30, 1000) if i not in used])
    ids = (f"{n:03d}", f"{n:03d}")  # corpus convention: msg number == thread number
    froms, subjs, prevs = cats[rng.choice(sorted(cats))]
    frm, subj = rng.choice(froms), rng.choice(subjs)
    if subj.startswith("This week in "):  # the digest subject names the sender's org
        subj = "This week in " + frm.split(" <")[0]
    body = header(rng, frm, subj, rng.choice(prevs), ids)
    return body + (established(rng) if member == DK else "")


DAYNAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
TZS = ["GMT-3", "GMT+13", "GMT+1", "GMT", "GMT-5", "GMT+9", "GMT+5:30", "GMT+2"]
AGENTS = ["main", "inbox", "desk", "assistant", "ops"]
CHANNELS = ["telegram", "whatsapp", "slack", "webchat", "signal", "discord"]


def openclaw_wrap(inner, rng):
    d = datetime.date(2026, 9, 1) + datetime.timedelta(days=rng.randint(0, 60))
    stamp = f"[{DAYNAMES[d.weekday()]} {d.isoformat()} {rng.randint(6, 22):02d}:{rng.choice([0, 5, 12, 30, 47]):02d} {rng.choice(TZS)}] "
    ch = rng.choice(CHANNELS)
    ctx_body = rng.choice([
        f"Conversation info (untrusted metadata):\n```json\n{{\"channel\": \"{ch}\", \"chat_id\": \"{rng.randint(10**8, 10**9)}\", \"sender\": \"owner\"}}\n```",
        f"Sender is the workspace owner. Channel: {ch}. Reply in the same language as the request.",
        f"Session: s-{rng.randint(1000, 9999)}\nMemory: 3 notes loaded\nChannel: {ch}",
    ])
    ctx = f"<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>\n{ctx_body}\n<<<END_OPENCLAW_INTERNAL_CONTEXT>>>"
    footer = (f"\n\nRuntime: agent={rng.choice(AGENTS)} | host=mac-{rng.randint(1, 9)} | "
              f"channel={ch} | model=local/gemma-12b | thinking=off")
    if rng.random() < 0.5:
        return stamp + inner + "\n\n" + ctx + footer
    return ctx + "\n\n" + stamp + inner + footer


def unwrap(text):  # the gateway's own order of operations
    return _RUNTIME_FOOTER.sub("", _STAMP.sub("", _RUNTIME_CONTEXT.sub("", text).strip())).strip()


# ---- I3: content of another kind (not email headers)
FIRST = ["Marta", "Kenji", "Aisha", "Lars", "Paulo", "Ngaio", "Fiona", "Omar", "Bea", "Hugo", "Yuki", "Sipho"]


def other_kind(rng):
    k = rng.randrange(10)
    n = rng.randint(100, 99999)
    who = rng.choice(FIRST)
    if k == 0:
        return (f"DELIVERY NOTE DN-{n}\nDeliver to: Unit {rng.randint(1, 40)}, {rng.choice(['Kaiwharawhara Rd, Wellington', 'Hafenstraße 12, Hamburg', 'Calle Mayor 8, Zaragoza'])}\n"
                f"Items: {rng.randint(2, 60)} x {rng.choice(['A4 paper boxes', 'pallet wrap rolls', 'LED panels', 'office chairs'])}\n"
                f"Received by: {who}\nCondition: {rng.choice(['good', 'one carton damaged', 'complete'])}")
    if k == 1:
        return (f"Lab report #{n}\nPatient ref: P-{rng.randint(1000, 9999)}\nTest: {rng.choice(['HbA1c', 'Ferritin', 'TSH', 'Vitamin D'])}\n"
                f"Result: {rng.uniform(1, 90):.1f} {rng.choice(['mmol/mol', 'ng/mL', 'mIU/L', 'nmol/L'])}\nCollected: 2026-09-{rng.randint(10, 29)}\nFlag: {rng.choice(['normal', 'high', 'low'])}")
    if k == 2:
        return (f"SHIPPING MANIFEST — Vessel {rng.choice(['MV Tasman Star', 'MSC Aurora', 'Ever Gentle'])}, voyage {rng.randint(10, 99)}{rng.choice('NSEW')}\n"
                f"Container {rng.choice(['MSKU', 'TGHU', 'CMAU'])}{rng.randint(1000000, 9999999)}: {rng.randint(5, 30)} t {rng.choice(['frozen lamb', 'kiwifruit', 'machine parts', 'coffee beans'])}\n"
                f"Port of loading: {rng.choice(['Tauranga', 'Santos', 'Rotterdam'])}\nPort of discharge: {rng.choice(['Busan', 'Felixstowe', 'Durban'])}")
    if k == 3:
        a, b = rng.randint(20, 400), rng.randint(2, 15)
        return (f"A tank holds {a} litres of water. Water drains out at {b} litres per minute while a pipe adds "
                f"{rng.randint(1, b - 1) if b > 1 else 1} litres per minute. How long until the tank is empty?")
    if k == 4:
        return (f"Calendar entry\nTitle: {rng.choice(['Dentist', 'Quarterly planning', 'School pickup', 'Yoga'])}\n"
                f"When: {rng.choice(DAYNAMES)} {rng.randint(1, 28)} Oct 2026, {rng.randint(7, 18)}:00–{rng.randint(19, 21)}:00\n"
                f"Where: {rng.choice(['Room 4B', 'Zoom', 'Ponsonby Rd clinic', 'home'])}\nRepeat: {rng.choice(['never', 'weekly', 'monthly'])}")
    if k == 5:
        return (f"{who}: hey are we still on for {rng.choice(['dinner', 'the climb', 'the demo', 'band practice'])}?\n"
                f"me: yes! {rng.choice(['7ish', 'after work', 'around noon', 'whenever you like'])}\n"
                f"{who}: {rng.choice(['great, bringing snacks', 'cool see you there', 'perfect 👍', 'ok will tell the others'])}")
    if k == 6:
        return (f"Meeting minutes — {rng.choice(['Garden committee', 'Sprint retro', 'PTA', 'Safety review'])} #{n}\n"
                f"Attendees: {', '.join(rng.sample(FIRST, 3))}\nDecisions: {rng.choice(['repaint the shed', 'move standup to 9:30', 'buy a new projector', 'postpone the fair'])}\n"
                f"Actions: {who} to follow up")
    if k == 7:
        return (f"Recipe: {rng.choice(['Pavlova', 'Shakshuka', 'Pão de queijo', 'Dal tadka'])}\nServes: {rng.randint(2, 8)}\n"
                f"Ingredients: {rng.randint(3, 6)} eggs, {rng.randint(100, 400)} g {rng.choice(['sugar', 'tomatoes', 'tapioca flour', 'lentils'])}\nOven: {rng.randint(120, 220)} °C")
    if k == 8:
        return (f"sensor={rng.choice(['greenhouse-2', 'freezer-A', 'boiler-3'])} t=2026-09-{rng.randint(10, 29)}T{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}Z "
                f"temp={rng.uniform(-20, 40):.1f}C humidity={rng.randint(20, 95)}% battery={rng.randint(5, 100)}%")
    return (f"Train ticket\nPassenger: {who} {rng.choice(['Okoro', 'Lindgren', 'Moreau', 'Sato'])}\n"
            f"From {rng.choice(['Wien Hbf', 'Zürich HB', 'Milano Centrale'])} to {rng.choice(['München Hbf', 'Paris Est', 'Venezia S. Lucia'])}\n"
            f"Coach {rng.randint(1, 14)}, seat {rng.randint(1, 90)}{rng.choice('ABCD')}\nDeparts {rng.randint(5, 22):02d}:{rng.randint(0, 59):02d}")


# ---- C3: keyed foreign text + request
def keyed(rng):
    k = rng.randrange(7)
    n = rng.randint(1000, 999999)
    if k == 0:
        body = (f"Order ID: ORD-{n}\nCustomer: {rng.choice(FIRST)} {rng.choice(['Tui', 'Becker', 'Rossi', 'Kim'])}\n"
                f"Item: {rng.choice(['standing desk', 'espresso grinder', 'trail shoes', 'USB-C dock'])}\nQuantity: {rng.randint(1, 12)}\n"
                f"Shipping: {rng.choice(['express', 'standard', 'click & collect'])}\nStatus: {rng.choice(['paid', 'pending', 'on hold'])}")
        req = rng.choice(["Process this order.", "Can this ship today?", "What's the total if each costs $49?", "Refund this order."])
    elif k == 1:
        body = (f"Ticket: SUP-{n}\nPriority: {rng.choice(['P1', 'P2', 'P3', 'low'])}\nComponent: {rng.choice(['billing', 'login', 'mobile app', 'exports'])}\n"
                f"Reporter: {rng.choice(FIRST)}\nDescription: {rng.choice(['page hangs on save', 'cannot reset password', 'CSV has wrong encoding', 'charged twice'])}")
        req = rng.choice(["Assign this to the right team.", "What is the priority of this ticket?", "Suggest a fix.", "Close this ticket as a duplicate."])
    elif k == 2:
        body = (f"host: db-{rng.randint(1, 9)}.internal\nport: {rng.choice([5432, 3306, 6379, 27017])}\nmax_connections: {rng.randint(10, 500)}\n"
                f"timeout_ms: {rng.randint(100, 30000)}\ntls: {rng.choice(['true', 'false'])}")
        req = rng.choice(["Is this config valid?", "Convert this to JSON.", "What would you change for production?", "Explain each setting."])
    elif k == 3:
        body = (f"Booking ref: {rng.choice('ABCDEFGH')}{n}\nGuest: {rng.choice(FIRST)}\nCheck-in: 2026-10-{rng.randint(1, 28):02d}\n"
                f"Nights: {rng.randint(1, 9)}\nRoom: {rng.choice(['double', 'twin', 'suite'])}\nBreakfast: {rng.choice(['yes', 'no'])}")
        req = rng.choice(["What's the check-out date?", "Change this to two guests.", "Cancel this booking.", "How much at €120 a night?"])
    elif k == 4:
        body = (f"Name: {rng.choice(FIRST)} {rng.choice(['Ahmed', 'Novak', 'Silva', 'Walker'])}\nPosition: {rng.choice(['data analyst', 'nurse', 'site engineer', 'chef'])}\n"
                f"Experience: {rng.randint(0, 25)} years\nAvailability: {rng.choice(['immediate', '1 month', '3 months'])}\nSalary expectation: {rng.randint(40, 160)}k")
        req = rng.choice(["Should we interview this applicant?", "Summarise this application.", "Rank this candidate 1–5.", "Draft a rejection letter."])
    elif k == 5:
        body = (f"Bug: BUG-{n}\nEnvironment: {rng.choice(['iOS 19', 'Android 16', 'Firefox 140', 'Windows 12'])}\nSteps: {rng.choice(['open settings, tap export', 'upload a 2GB file', 'switch language twice'])}\n"
                f"Expected: {rng.choice(['file saves', 'upload completes', 'labels update'])}\nActual: {rng.choice(['crash', 'spinner forever', 'blank screen'])}")
        req = rng.choice(["Write a reproduction test for this.", "How severe is this?", "Who should own this bug?", "Rewrite this bug report more clearly."])
    else:
        body = (f"SKU: {rng.choice(['KB', 'MS', 'HD'])}-{n}\nWarehouse: {rng.choice(['Auckland', 'Leipzig', 'Monterrey'])}\nOn hand: {rng.randint(0, 900)}\n"
                f"Reorder point: {rng.randint(20, 200)}\nLead time: {rng.randint(2, 40)} days")
        req = rng.choice(["Do we need to reorder?", "When will we run out at 15 a day?", "Update the reorder point to 50.", "Is this stock level healthy?"])
    return body + "\n\n" + req if rng.random() < 0.7 else req + "\n\n" + body


# ---- D3: plain requests (no email)
D3_BASE = [
    "What's a good substitute for buttermilk in pancakes?",
    "Write a Python function that checks whether a string is a palindrome.",
    "Plan a 3-day trip to Kyoto in November on a mid-range budget.",
    "Explain the difference between TCP and UDP like I'm new to networking.",
    "How long should I boil an egg for a jammy yolk?",
    "What's the capital of Burkina Faso?",
    "Give me a 20-minute bodyweight workout I can do in a hotel room.",
    "Convert 72 degrees Fahrenheit to Celsius.",
    "Write a haiku about the first frost.",
    "Why does my sourdough come out flat?",
    "How do I undo the last git commit but keep the changes?",
    "Recommend three sci-fi novels for someone who loved The Left Hand of Darkness.",
    "What's the best way to get from Lisbon airport to Alfama?",
    "Explain compound interest with a simple example.",
    "Write a SQL query that returns the top 5 customers by revenue.",
    "What should I pack for a week of hiking in Patagonia?",
    "Help me name a small bakery that sells Argentine pastries.",
    "Is it safe to eat rice that was left out overnight?",
    "Translate 'where is the train station' into Japanese.",
    "How do I center a div with CSS grid?",
    "Suggest a vegetarian dinner using chickpeas, spinach and coconut milk.",
    "What's the difference between a Roth IRA and a traditional IRA?",
    "Write a short bedtime story about a brave hedgehog.",
    "How many hours of sleep do teenagers need?",
    "Explain what a hash map is and when to use one.",
    "Best time of year to visit Iceland for the northern lights?",
    "Give me a regex that matches a New Zealand phone number.",
    "What are some good icebreakers for a team offsite?",
    "How do I repot a fiddle-leaf fig without killing it?",
    "Summarise the plot of Hamlet in five sentences.",
    "What does 'idempotent' mean in REST APIs?",
    "Write a limerick about a cat who hates Mondays.",
    "How do I make cold brew coffee at home?",
    "Recommend a beginner-friendly road bike under $1000.",
    "What's the time difference between Auckland and Buenos Aires?",
    "Write a bash one-liner to find the 10 largest files in a directory.",
    "How can I improve my posture while working at a desk?",
    "Explain the rules of cricket briefly.",
    "What's a good gift for a friend who just moved into a new flat?",
    "How do vaccines train the immune system?",
    "Suggest a weekend itinerary for Edinburgh with kids.",
    "Fix this: TypeError: 'NoneType' object is not subscriptable — what usually causes it?",
    "How do I calculate the area of a circle with a 7 cm radius?",
    "Give me five tips for learning Portuguese faster.",
    "What's the healthiest way to cook broccoli?",
    "Write a cover letter opening line for a UX designer role.",
    "How does a heat pump work?",
    "What are the main differences between Rust and Go?",
    "Recommend some podcasts about economics.",
    "How do I stop my glasses fogging up with a mask?",
    "Make a packing list for a beach holiday in Bali.",
    "What's a polite way to decline a wedding invitation?",
    "Explain the Monty Hall problem.",
    "Write a JavaScript debounce function.",
    "How should I store fresh herbs so they last longer?",
    "What's the population of Montevideo?",
    "Teach me how to tie a bowline knot.",
    "Give me a meal plan for a week of high-protein lunches.",
    "Explain Kubernetes pods vs deployments.",
    "Which national parks in Chile are worth visiting?",
]
D3_WRAP = ["{q}", "Quick question: {q}", "Hey! {q}", "{q} Thanks!", "Can you help? {q}", "{q} Keep it short please."]


# --------------------------------------------------------------------------- assemble
def fill(n, make, rng, seen):
    out = []
    tries = 0
    while len(out) < n:
        tries += 1
        assert tries < n * 200, "could not reach target without duplicates"
        text, truth = make(rng)
        if text and text not in seen:
            seen.add(text)
            out.append([text, truth])
    return out


def build():
    rng = random.Random(SEED)
    seen = set()
    sets = {}

    def per_member(make):
        rows = []
        for m in MEMBERS:
            rows += fill(60, lambda r, m=m: make(m, r), rng, seen)
        return rows

    sets["A3"] = per_member(lambda m, r: (corpus_content(m, r) + "\n\n" + TASK[m], m))
    sets["F3"] = per_member(lambda m, r: (fresh_content(m, r) + "\n\n" + TASK[m], m))
    sets["G3"] = per_member(lambda m, r: (TASK[m] + "\n\n" + fresh_content(m, r), m))
    sets["H3"] = per_member(lambda m, r: (openclaw_wrap(fresh_content(m, r) + "\n\n" + TASK[m], r), m))
    sets["E3"] = per_member(lambda m, r: (fresh_content(m, r) + "\n\n" + r.choice(OTHER_TASKS), OUT))
    sets["E4"] = per_member(lambda m, r: (fresh_content(m, r) + "\n\n" + TASK[m] + "\n\n" + r.choice(SECOND_INSTR), OUT))
    sets["I3"] = per_member(lambda m, r: (other_kind(r) + "\n\n" + TASK[m], OUT))
    sets["C3"] = fill(120, lambda r: (keyed(r), OUT), rng, seen)
    sets["D3"] = fill(120, lambda r: (r.choice(D3_WRAP).format(q=r.choice(D3_BASE)), OUT), rng, seen)
    sets["B3"] = per_member(lambda m, r: (fresh_content(m, r) + "\n\n" + r.choice(PARAPHRASE[m]), m))
    return sets


def validate(sets):
    expect = {"A3": 120, "F3": 120, "G3": 120, "H3": 120, "E3": 120, "E4": 120,
              "I3": 120, "C3": 120, "D3": 120, "B3": 120}
    member_sets = {"A3", "F3", "G3", "H3", "B3"}
    assert set(sets) == set(expect)
    all_texts = []
    for name, rows in sets.items():
        assert len(rows) == expect[name], (name, len(rows))
        for text, truth in rows:
            assert isinstance(text, str) and text.strip(), name
            assert truth in (EF, DK, OUT), (name, truth)
            assert (truth in MEMBERS) == (name in member_sets), (name, truth)
            all_texts.append(text)
        has_task = [TASK[EF] in t or TASK[DK] in t for t, _ in rows]
        if name in {"A3", "F3", "G3", "H3", "E4", "I3"}:
            assert all(has_task), name          # the exact member task is present
        if name in {"E3", "B3", "C3", "D3"}:
            assert not any(has_task), name      # the exact member task is absent
        if name in member_sets:
            assert sum(t == EF for _, t in rows) == 60 and sum(t == DK for _, t in rows) == 60, name
    assert len(all_texts) == len(set(all_texts)), "duplicate texts"
    assert len(set(OTHER_TASKS)) >= 20
    assert all(len(set(PARAPHRASE[m])) >= 15 for m in MEMBERS)
    assert not set(PARAPHRASE[EF] + PARAPHRASE[DK] + OTHER_TASKS) & {TASK[EF], TASK[DK]}
    # Fresh material must not reuse the corpora's senders, subjects or previews.
    corpus_from = set().union(*(set(POOLS[m][0]) for m in MEMBERS))
    corpus_subj = set().union(*(set(POOLS[m][1]) for m in MEMBERS))
    corpus_prev = set().union(*(set(POOLS[m][2]) for m in MEMBERS))
    fresh_from = {f"{n} <{a}>" for n, a in PEOPLE + AUTOMATED}
    assert not fresh_from & corpus_from
    assert not set(EF_SUBJECTS + DK_SUBJECTS) & corpus_subj
    assert not set(EF_PREVIEWS + DK_PREVIEWS) & corpus_prev
    corpus_domains = {a.split("@")[1].rstrip(">") for a in corpus_from}
    assert not {a.split("@")[1] for _, a in PEOPLE + AUTOMATED} & corpus_domains
    for name in ("F3", "G3", "H3", "E3", "E4", "B3"):
        for text, _ in sets[name]:
            for ln in text.split("\n"):
                if ln.startswith("From: "):
                    assert ln[6:] not in corpus_from, (name, ln)
    # A3 really is corpus-shaped: pools from the corpus, new numbers, msg == thr.
    for text, truth in sets["A3"]:
        used = POOLS[truth][3]
        a, b = re.match(r"Message msg-(\d+) in thread thr-(\d+)\n", text).groups()
        assert a == b and int(a) not in used
        assert text.endswith("\n\n" + TASK[truth])
    # H3 unwraps (with the gateway's own regexes) to exactly an F3-shaped request.
    for text, truth in sets["H3"]:
        inner = unwrap(text)
        assert inner != text and inner.startswith("Message msg-") and inner.endswith("\n\n" + TASK[truth])
        assert "OPENCLAW" not in inner and "Runtime:" not in inner
    # G3 puts the task first; E4 has the task followed by another paragraph.
    assert all(t.startswith(TASK[y] + "\n\n") for t, y in sets["G3"])
    assert all(("\n\n" + TASK[EF] + "\n\n" in t) or ("\n\n" + TASK[DK] + "\n\n" in t) for t, _ in sets["E4"])
    # I3 / C3 / D3 carry no email header lines.
    for name in ("I3", "C3", "D3"):
        for text, _ in sets[name]:
            assert not re.search(r"^(Message msg-|From: |Subject: |Preview: )", text, re.M), (name, text)


def main():
    sets = build()
    validate(sets)
    out = HERE / "sets.json"
    out.write_text(json.dumps(sets, ensure_ascii=False, indent=1))
    total = 0
    for name, rows in sets.items():
        counts = {}
        for _, t in rows:
            counts[t] = counts.get(t, 0) + 1
        total += len(rows)
        print(f"{name}: {len(rows)} {counts}")
    print(f"total: {total} rows -> {out}")
    ex_rng = random.Random(SEED + 1)
    for name, rows in sets.items():
        text, truth = rows[ex_rng.randrange(len(rows))]
        print(f"\n===== {name} example (truth={truth}) =====\n{text}")


if __name__ == "__main__":
    main()
