---
name: ig-reply
description: >-
  Handle the comments under the user's own reels and posts - draft replies to
  the ones worth answering, sorted by which ones are. Use when the user pastes
  their comments, says "reply to these", "handle my comments", "someone said X
  on my reel", or is dealing with a critic, a hater or a lead in the comments.
---

# ig-reply

## Content language

Use the language explicitly requested for this content, then the selected
account's voice profile; otherwise follow the supplied text or conversation.
Do not guess from a competitor's handle. For mixed content, ask for the main
language when it matters. Preserve Turkish characters, names, currency and the
brand's tone; do not translate English templates literally.
Pass `--language tr` or `--language en` explicitly to humanize, detect, hookscore,
beats, caption and swipe. The CLI default stays English for compatibility.
For Turkish, use `slop.tr.json` and `hooks.tr.json`; unavailable checks are N/A.
English contractions and explicit pronouns are not requirements for Turkish.
Use approved Turkish brand examples for manual voice review; do not rewrite
just to raise a score. Turkish scores are provisional editorial signals,
not validated performance predictions or AI-authorship detection.

## Account context

For account-specific work, resolve the user's publishing handle from the request
or established conversation, not a research target or message recipient. Run
`../ig-account/account.py show --account HANDLE` with Python from this skill's
folder (or use the helper's absolute installed path). Without an established
handle, run `show` without `--account`: legacy paths work only when no named
accounts exist; otherwise ask which publishing account to use.
Use only the returned paths, read that account's voice when relevant, and pass
the same handle to downstream skills. Missing files never fall back to another
account. On switching accounts, discard the previous account's context. Include
`account: @HANDLE` in receipts for saved work. Text-only edits need no selection
unless they use saved brand context. If the helper is unavailable, work from
supplied text without saved context or filesystem writes; install the full pack
for persistent profiles. See [account setup](../ig-account/SKILL.md).

The comment thread under your own post is where reach is decided. Every reply
is another interaction on the post, replies arriving in the first hour do most
of the work, and on Instagram a reply can also be a Reel, which is the single
most underused move on the platform.

But the value is not equal across comments, so this skill sorts before it
writes.

## Input

The user pastes the comments, ideally with handles. Screenshots are fine. Do
not scrape the thread with a browser tool.

## Triage first

Sort every comment into one of six buckets and say the counts out loud:

| bucket | what it is | what it gets |
| --- | --- | --- |
| **KEYWORD** | the word you asked them to comment | the promised thing, sent by hand or by your approved tool |
| **LEAD** | someone describing the problem you solve | a real answer in public, then a door |
| **SUBSTANCE** | adds data, disagrees, extends | the longest reply on the thread |
| **QUESTION** | a question a lot of people have | this one becomes a Reel, not just a reply |
| **SUPPORT** | "🔥", "great post", a tag | a like, and 3 to 8 words at most |
| **NOISE** | pitch, spam, bad faith, bait | nothing, or one line and out |

Write in that order and stop when the value stops.

## The move most people miss

If a question in the comments is one that thirty other people also have,
**reply to it with a Reel**. Instagram will attach the comment to the new video
as a sticker, the person who asked gets notified, and a question with real
demand behind it becomes a post with the hook already written for you. Flag
every QUESTION that qualifies and hand it to `/ig-reel` as formula #16.

## How to reply

- **Answer the actual question.** If someone asks how, tell them how, in the
  reply. Do not send them to the DMs to hear an answer they could have had.
- **Use their name once**, at the start, without an exclamation mark.
- **Match their length.** A four-word comment does not get a four-line reply.
- **To a critic:** concede the true part first, in their words, then hold the
  line. Never delete, never get defensive, never reply twice on the same
  thread.
- **To a hater:** nothing. A reply is reach, and reach is what they came for.
  Hide the comment if it is abusive. Instagram's comment controls exist and
  using them is not losing.
- **To a lead:** answer fully in public. The door is one sentence at the end
  and it is an offer of help, not a pitch. The public answer is what makes the
  next person DM you.

## Keyword comments

If the post used a keyword ask, those comments are the whole point of the post.
Every one of them is a person who raised their hand. Reply to each, then send
what was promised. If the user has automation set up through Instagram's own
tools or an approved partner, say so and let it run; if not, the replies are
manual and that is fine at this volume. Never bulk-DM people who did not
comment.

## Output

One block, grouped by bucket, each reply copy-ready and already humanized:

```
REPLIES  ·  84 comments  ·  41 KEYWORD, 2 LEAD, 3 SUBSTANCE, 2 QUESTION, 34 SUPPORT, 2 NOISE

KEYWORD  (41)  send the clause. One line each, same warmth, not copy-paste.

LEAD
@handle - "we had this exact thing happen in June"
> The bit that fixed it for us was moving the payment trigger off approval
> entirely. Happy to send the wording if it is useful.

QUESTION -> REEL
@handle - "what do you do if they refuse to sign it?"
  34 likes on this comment. That is a Reel, not a reply. Formula #16.

NOISE  (2)  skipped. Replying gives them reach.
```

Then the gate: nothing is posted until the user says yes. They paste the
replies.
