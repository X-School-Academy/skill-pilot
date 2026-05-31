# Category: Maths — Types

Showcases in this category teach a maths concept by letting the user **first build or run a small computer-science product**, then explore the underlying maths afterwards. Source material: `workspace/tasks/showcases/math_use_cases_in_computer_science.md`.

Primary audiences:

- Students and self-learners who want maths to feel concrete.
- AI agent learners who need an intuition for vectors, matrices, probability.
- Teachers building short demos or projects for classrooms.

## Types

### M1. Maths algorithms in real products

- **What it is:** Pick a real-world digital product (QR code, JPEG, GPS, Dijkstra map, hashing, RAG search) and ship a tiny working demo of it.
- **Maths focus:** binary encoding, error-correction codes, hashing, graph algorithms, vector similarity.
- **Example showcases:**
  - Build a QR code generator + scanner and explain Reed–Solomon error correction.
  - Build a shortest-path map demo using Dijkstra / A* on a 20-node graph.
  - Build a mini RAG search over 10 documents using cosine similarity on embeddings.
- **Terms:** binary, matrix, error correction, hashing, graph, embeddings, cosine similarity.

### M2. Algebra in computer science

- **What it is:** Demonstrate one branch of algebra (Boolean, linear, matrix, modular, polynomial, relational, set) through code the user can run.
- **Maths focus:** algebraic operations as transformations of information.
- **Example showcases:**
  - Boolean algebra — interactive truth-table playground tied to a login-permission example.
  - Linear algebra — AI embeddings visualiser ("cat", "dog", "car" as 3D vectors).
  - Matrix algebra — rotate/scale a 3D model with a hand-written transform matrix.
  - Modular algebra — clock-arithmetic demo that becomes a tiny RSA toy.
  - Polynomial algebra — corrupt a QR code by hand and watch it recover.
  - Relational algebra — convert SQL queries into select / project / join steps.
- **Terms:** vector, matrix, modulus, group, ring, field, polynomial, relational algebra.

### M3. Signal processing

- **What it is:** Turn a real-world signal (sound, image, sensor data) into digital information and back.
- **Maths focus:** sampling, Fourier transform, convolution, modulation, filtering.
- **Example showcases:**
  - Sound-wave Wi-Fi config: send a short string from phone to laptop using audio frequencies.
  - Music visualiser driven by live FFT bands.
  - Noise-cancellation demo: play wave A and wave –A and measure cancellation.
  - Speech-to-spectrogram viewer; feed the spectrogram to a tiny classifier.
  - Image-filter playground (blur / sharpen / edge detection) using 3×3 kernels.
- **Terms:** sampling, frequency, FFT, modulation, convolution, kernel, spectrogram.

### M4. University-level maths topics

- **What it is:** Pick one university-level area (discrete maths, probability, calculus, optimisation, information theory, automata theory, control theory, queueing) and ship a focused demo that shows where it lives in real software.
- **Maths focus:** topic-specific — see table below.
- **Example showcases:**
  - Discrete maths — visualise a Git commit graph as a DAG with traversal demo.
  - Probability — naive-Bayes spam classifier on 200 emails.
  - Calculus — gradient-descent demo training y = mx + b on noisy data.
  - Optimisation — solve a delivery-routing puzzle with constraints.
  - Information theory — interactive Huffman-coding compressor.
  - Automata theory — visualise a regex as a state machine.
  - Control theory — keep a simulated drone hovering with a PID loop.
  - Queueing theory — simulate users waiting on N servers and chart latency.
- **Terms:** graph, DAG, Bayes, gradient descent, entropy, Huffman, NFA/DFA, PID, M/M/1 queue.

### M5. Teaching-style mini courses

- **What it is:** Bundle a maths topic into a short interactive lesson — explainer, demo, and a short assignment — produced via `course-creator`.
- **Maths focus:** any of M1–M4, but packaged for a learner rather than a builder.
- **Example showcases:**
  - "Why QR codes still scan when torn" — 15-minute interactive lesson with a graded exercise.
  - "Maths inside Google Maps" — explainer + Dijkstra coding lab.
  - "Algebra you already use every day" — 5 short demos in one course.
- **Terms:** lesson plan, formative assessment, worked example, spaced repetition.

## Cross-cutting variants

These axes can be applied to any type above to create a meaningfully different showcase:

- **Output modality:** static webpage demo · interactive notebook · short video · slide deck · graded course.
- **Audience level:** middle-school · high-school · undergraduate · self-learner refresher.
- **Failure-mode framing:** start from a deliberately broken demo (corrupted QR code, wrong matrix order, missing FFT window) and let the user diagnose it.
