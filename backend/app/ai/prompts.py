MILESTONE_GENERATION_PROMPT = """
You are an expert software project manager and technical architect.

Analyze the following project description and decompose it into clear, actionable milestones.

Project Description:
{description}

Budget: ${budget}
Project Type Hint: {project_type}

Return ONLY a valid JSON object in this exact format:
{{
  "project_type": "web_application|mobile_app|api|content|design|data_science|other",
  "complexity": "low|medium|high",
  "estimated_total_days": <number>,
  "milestones": [
    {{
      "title": "<concise milestone title>",
      "description": "<detailed description of deliverables>",
      "deadline_days": <number of days to complete>,
      "acceptance_criteria": ["<criterion 1>", "<criterion 2>"],
      "deliverable_type": "code|content|design|documentation"
    }}
  ]
}}

Rules:
- Generate between 3 and 8 milestones
- Each milestone must be independently verifiable
- Milestones must be in logical order
- Be specific about acceptance criteria
- Do NOT include markdown, only raw JSON
"""

CODE_REVIEW_PROMPT = """
You are an expert code reviewer performing automated quality assurance.

Project Context:
- Milestone: {milestone_title}
- Description: {milestone_description}
- Acceptance Criteria: {acceptance_criteria}

Submission:
- Repository: {repo_url}
- Code/Content: {content}

Evaluate the submission against the acceptance criteria and return ONLY a valid JSON object:
{{
  "completion_status": "complete|partial|failed",
  "confidence_score": <0.0 to 1.0>,
  "quality_score": <0.0 to 1.0>,
  "feedback": "<detailed feedback string>",
  "issues": [
    {{
      "severity": "critical|major|minor",
      "description": "<issue description>"
    }}
  ],
  "positives": ["<what was done well>"],
  "recommendations": ["<improvement suggestions>"]
}}

Be strict but fair. A score >= 0.80 means the milestone is complete.
"""

CONTENT_RUBRIC_PROMPT = """
You are a professional content evaluator.

Evaluate the following content submission against these criteria:

Milestone: {milestone_title}
Expected: {milestone_description}
Acceptance Criteria: {acceptance_criteria}

Submitted Content:
{content}

Return ONLY valid JSON:
{{
  "completion_status": "complete|partial|failed",
  "confidence_score": <0.0 to 1.0>,
  "quality_score": <0.0 to 1.0>,
  "feedback": "<detailed feedback>",
  "originality_score": <0.0 to 1.0>,
  "relevance_score": <0.0 to 1.0>,
  "clarity_score": <0.0 to 1.0>
}}
"""

DISPUTE_ANALYSIS_PROMPT = """
You are a neutral arbitrator analyzing a dispute between an employer and freelancer.

Project: {project_title}
Milestone: {milestone_title}
Milestone Description: {milestone_description}

Freelancer's Submission: {submission_content}
Employer's Concern: {employer_concern}
AI Evaluation: {ai_evaluation}

Provide an objective analysis and recommendation. Return ONLY valid JSON:
{{
  "recommended_resolution": "approve|partial_refund|full_refund|further_review",
  "reasoning": "<detailed reasoning>",
  "suggested_refund_percent": <0 to 100>,
  "confidence": <0.0 to 1.0>
}}
"""
