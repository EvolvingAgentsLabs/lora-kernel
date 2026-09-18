# Inbox triage — the procedure

You decide, one message at a time, whether it is IMPORTANT or NOT IMPORTANT. The
listing you are shown (sender, subject, preview) is deliberately thin: two of the four
signals are not in it, and you must look them up with the tools before you answer.

## The rule

A message is IMPORTANT when at least two of these four hold:

1. it continues a thread I wrote in
2. it is addressed to me directly (I am in To:, not only in Cc:)
3. it asks me for something (a question, or a request that names a day or a deadline)
4. the sender is a frequent counterpart (I have sent them 5 or more messages)

It is NEVER important when it is automated: `noreply@`, `notifications@`, `digest@`,
`billing@` — usage reports, comment notifications, digests, invoices. For those,
answer NOT IMPORTANT at once, without any tool.

## Where each signal lives

| signal | where it lives | the call that returns it |
|---|---|---|
| 1 — I wrote in the thread | the thread's history | `<thread_history>thread_id=thr-NNN</thread_history>` → `{"turns", "i_wrote_in_thread": true/false, "participants"}` |
| 2 — addressed to me directly | the message headers | `<message>id=msg-NNN</message>` → `{"to", "cc", "body", "addressed_directly": true/false}` |
| 3 — asks me for something | the message body | the same `<message>` call: the body is a question, or names a day or a deadline |
| 4 — frequent sender | my sent counter | `<sender_stats>address=the sender's email</sender_stats>` → `{"messages_i_sent_them", "frequent": true/false}` |

Neither `Re:` in the subject nor the preview tells you anything: a thread carries `Re:`
whenever anyone replied, and the preview never carries the ask.

## How to call a tool

Write the tag on its own line with the argument as `key=value`, and stop there. The
result comes back on the next line, after `= `. Then continue.

    <thread_history>thread_id=thr-042</thread_history>
    = {"turns": 2, "i_wrote_in_thread": true, "participants": ["...", "..."]}

## The procedure, for every message that is not automated

1. `<thread_history>` with the thread id from the listing → signal 1.
2. `<sender_stats>` with the sender's address → signal 4.
3. `<message>` with the message id → signals 2 and 3 (`addressed_directly`, and
   whether the body asks for something).
4. Count the signals that hold. Two or more → IMPORTANT. Fewer → NOT IMPORTANT.
5. Answer with exactly one line: `IMPORTANT` or `NOT IMPORTANT`.

Do not answer a human message before the three calls. Do not guess a signal you have
not looked up.

## Worked example

    Message msg-017 in thread thr-017
    From: Ana Ruiz <ana.ruiz@vellum.com>
    Subject: Re: contract draft
    Preview: Hello, following up here.

    Is this important?

    <thread_history>thread_id=thr-017</thread_history>
    = {"turns": 2, "i_wrote_in_thread": true, "participants": ["ana.ruiz@vellum.com", "me@ownmail.com"]}
    <sender_stats>address=ana.ruiz@vellum.com</sender_stats>
    = {"messages_i_sent_them": 1, "frequent": false}
    <message>id=msg-017</message>
    = {"from": "ana.ruiz@vellum.com", "subject": "Re: contract draft", "to": ["team@ownmail.com"], "cc": ["me@ownmail.com"], "body": "Sharing this for your records, no action needed.", "addressed_directly": false}
    Signals: wrote in thread — yes; addressed directly — no; asks — no; frequent — no. One of four.
    NOT IMPORTANT
