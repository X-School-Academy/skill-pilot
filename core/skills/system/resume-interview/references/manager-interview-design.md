# Manager Interview Design Guide

Use this reference to design or practice manager-style interviews for AI, LLM, backend, and agent candidates. The goal is to test whether a candidate has real engineering judgment, not only whether they can solve algorithm questions or list popular tools.

## Interview Simulation Mode

Use this mode when the user asks to simulate, practice, role-play, or do a mock interview.

Act as an IT hiring manager conducting an interview for the candidate. Run the interview as a live conversation:

- start by stating the target role and interview format if known
- ask one question at a time
- wait for the candidate's answer before moving on
- ask realistic follow-up questions based on the answer
- probe for production judgment, not only tool familiarity
- keep the tone professional, direct, and manager-like
- do not reveal the full rubric during the interview unless the user asks
- delay detailed scoring and coaching until the user says the interview is finished, the planned segment is complete, or feedback is requested

If the user did not provide a target role, default to an AI / LLM / backend engineer interview. If the user did not provide a resume or project, start with a project deep-dive prompt and let the candidate choose a project.

Suggested opening:

> I will act as the IT hiring manager. We will run this like a real interview: I will ask one question at a time, follow up based on your answers, and give feedback at the end. First, choose one AI or backend project from your resume. What real user problem did it solve?

## Core Interview Goal

As a manager, evaluate whether the candidate can turn an unclear requirement into a reliable small production system.

The interview should test:

- requirement clarification
- system decomposition
- coding quality
- error handling
- edge cases
- latency and cost awareness
- AI and LLM engineering judgment
- ability to explain tradeoffs
- maintainability and future extension

## 1. Project Deep Dive - 15 Minutes

Ask the candidate to choose one AI or backend project from their resume.

### Questions

- What real user problem did this project solve?
- Who were the users?
- How many users, requests, documents, or sessions did it support?
- What was the latency requirement?
- What could go wrong in production?
- How did you monitor errors?
- How did you test the system?
- What part was hardest technically?
- What would you redesign if you had another month?

### Good Signals

Strong candidates talk about:

- system boundaries
- data flow
- failure cases
- latency
- cost
- logs and monitoring
- testing
- deployment
- security
- user experience

### Red Flags

Weak candidates only say:

- "I used OpenAI API"
- "I built a chatbot"
- "I used LangChain"
- "It worked"
- "The model generated the answer"

These answers suggest demo-level work rather than production-level work.

## 2. AI System Design Question - 25 Minutes

Give a practical AI engineering problem.

Example:

> Design an AI academic advisor system for university students. Students can ask questions such as "Can I take COMP3900 next term?", "What courses should I choose if I want to become an AI engineer?", and "Am I eligible to graduate next year?" The system should use university course rules, student transcript data, and LLM reasoning. Design the backend system.

### What You Want to See

The candidate should not jump directly to "use GPT plus RAG." They should clarify:

- Are answers advisory only or official?
- Is student data private?
- Do we need citations from university documents?
- How fresh is course data?
- What is the expected latency?
- How many students use it?
- What should happen if the system is uncertain?
- Do we need human review for risky answers?

### Expected Architecture

A strong answer may include:

```text
User Question
   ↓
Auth / Student Identity
   ↓
Input Validation
   ↓
Intent Classification
   ↓
Retrieve Student Transcript
   ↓
Retrieve Course Rules / Handbook Data
   ↓
RAG Retrieval Pipeline
   ↓
LLM Reasoning / Advisor Agent
   ↓
Validation Layer
   ↓
Citations + Confidence Score
   ↓
Final Answer
   ↓
Logging / Monitoring / Feedback
```

## 3. Tradeoff Questions - 15 Minutes

Use follow-up questions to test real engineering judgment.

### RAG vs Fine-Tuning

Question:

> Why would you use RAG instead of fine-tuning?

Good answer:

- course rules change often
- citations are needed
- fresh information is needed
- fine-tuning is not good for frequently changing factual knowledge
- RAG is easier to update and audit

Weak answer:

- "Because RAG is popular"
- "Because LangChain supports it"

### Single Agent vs Multi-Agent

Question:

> Why not just use one LLM call?

Good answer:

- a single agent is simpler and cheaper
- multi-agent systems can help when tasks are clearly separated
- multi-agent systems increase latency, cost, and debugging difficulty
- use multi-agent only for clear roles such as retrieval, validation, planning, and policy checking

Weak answer:

- "Multi-agent sounds more advanced"
- "Because AutoGPT uses agents"

### Latency Control

Question:

> If the system is too slow, how would you reduce latency?

Strong answers may include:

- cache common answers
- use a smaller router model
- reduce retrieved chunks
- parallelize retrieval
- stream partial responses
- pre-index documents
- pre-compute student eligibility facts
- avoid unnecessary agent loops
- use model routing with a small model first and a large model only when needed

### Failure Handling

Question:

> What if retrieval returns the wrong document?

Good answer:

- show citations
- validate the answer against retrieved sources
- use confidence thresholds
- ask clarification when uncertain
- fall back to a human advisor
- log failure cases for evaluation

## 4. Coding Task - 30 to 45 Minutes

Use a small production-like implementation task instead of only a LeetCode-style question.

Example:

> Implement `answer_student_question(user_id, question)`. It should validate input, detect the question type, retrieve relevant documents, call an LLM client, handle timeout or API failure, and return structured output. You can mock the LLM and retrieval functions.

### What You Are Testing

Evaluate:

- function decomposition
- naming
- simple structure
- error handling
- timeout handling
- edge cases
- testability
- whether the candidate avoids one giant function
- whether they write clean interfaces

### Strong Candidate Code Shape

```python
def answer_student_question(user_id: str, question: str) -> AdvisorResponse:
    validate_input(user_id, question)

    intent = classify_intent(question)
    student_profile = get_student_profile(user_id)
    documents = retrieve_relevant_documents(question, intent)

    if not documents:
        return fallback_response("I could not find reliable course information.")

    llm_result = generate_answer(
        question=question,
        student_profile=student_profile,
        documents=documents,
    )

    return validate_and_format_response(llm_result, documents)
```

A weaker candidate writes everything inside one long function with no clear boundaries.

## 5. Edge Case Questions

Ask these after coding or system design.

### Input Edge Cases

- What if the user asks a vague question?
- What if the student transcript is missing?
- What if the course rule document is outdated?
- What if the user asks something outside the system scope?
- What if the user enters malicious prompt injection?
- What if the LLM gives a confident but wrong answer?

### Production Edge Cases

- What if the OpenAI API is down?
- What if retrieval is slow?
- What if the vector database returns irrelevant results?
- What if the same student asks 100 questions in one minute?
- What if the answer affects graduation eligibility?

## 6. Evaluation and Testing Question

Ask:

> How would you evaluate whether this AI advisor is actually good?

Strong answer:

- create golden test cases
- test factual accuracy
- test citation correctness
- test hallucination rate
- test latency
- test cost per request
- test retrieval quality
- collect human advisor feedback
- track user correction rate
- evaluate risky cases separately

Weak answer:

- "I will ask GPT if the answer is good"
- "I will manually test a few examples"

## 7. Manager Scoring Rubric

| Area | Strong Signal | Weak Signal |
| --- | --- | --- |
| Requirement clarification | Asks about users, risk, latency, data, and scope | Starts coding immediately |
| System design | Breaks system into clean components | Says "use GPT plus database" |
| AI judgment | Explains RAG, routing, evaluation, and hallucination | Only lists tools |
| Coding | Small functions, clean names, and error handling | One large messy function |
| Edge cases | Thinks about failure and ambiguity | Only handles happy path |
| Production sense | Mentions logging, monitoring, deployment, and cost | Demo-only thinking |
| Communication | Explains tradeoffs clearly | Uses buzzwords without depth |

## 8. Final Manager Decision Guide

### Hire Signal

The candidate is strong if they can say things like:

> I would first keep the system simple. I do not want multi-agent unless the workflow clearly needs separate reasoning steps. For course advice, I would use RAG because the rules change often and we need citations. I would add a validation layer because wrong academic advice is high risk. For latency, I would cache common retrieval results and use a smaller model for routing.

### Reject or Concern Signal

Be careful if the candidate says:

> I will use LangChain, GPT-4, FAISS, and agents.

but cannot explain:

- why this architecture
- what can fail
- how to test it
- how to reduce latency
- how to handle wrong answers
- how to maintain the system

That usually means the candidate has project keywords but not production experience.

## Best Interview Question to Use

Ask:

> You built an AI course advisor. It works in your demo. Now we want to release it to 10,000 students. What must change before production?

A strong candidate will talk about:

- auth
- privacy
- logging
- monitoring
- cost
- latency
- evaluation
- fallback
- human escalation
- rate limiting
- prompt injection
- data freshness
- citations
- system reliability

A weak candidate will only say:

- "Use a better model"
- "Deploy it on AWS"
- "Add more data"

This is the difference between project experience and engineering experience.
