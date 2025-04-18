from scoring.module import ScoreModule

class Crossword(ScoreModule):
    INITIAL_SCORE = 100
    HINT_INTERACTION = "question_hint"

    def __init__(self, play_id, instance, play=None):
        super().__init__(play_id, instance, play)
        self.points_lost = 0.0
        self.hint_deductions = 0.0
        self.modifiers = {}  # key: re-indexed question id (string), value: deduction percentage
        self.scores = {}     # key: re-indexed question id, value: raw score
        self.question_counter = 0  # counter to assign sequential question ids for logs
        self.modifier_count = 0
        self.can_interact = False




    def handle_log_question_answered(self, log):
        self.can_interact = True
        raw_item_id = log.item_id if hasattr(log, "item_id") else log["item_id"]
        item_id = str(raw_item_id)

        # Normalize text
        text = (log.text if hasattr(log, "text") else log["text"]).lower()
        if hasattr(log, "text"):
            log.text = text
        else:
            log["text"] = text


        # Perform scoring logic ONCE
        score = self.check_answer(log)
        self.scores[item_id] = score

        # Update totals once here
        self.total_questions += 1
        self.verified_score += score


    def check_answer(self, log):
        item_id = str(log.item_id if hasattr(log, "item_id") else log["item_id"])
        if item_id not in self.questions:
            print(f"ERROR: Item ID '{item_id}' not found in self.questions!")
            return 0

        question = self.questions[item_id]
        if not question["answers"]:
            print(f"⚠️ No answers found for question with id {item_id}.")
            return 0

        correct_text = question["answers"][0]["text"]
        submitted_text = (log.text if hasattr(log, "text") else log["text"]).lower()

        answer_chars = self.normalize_string(correct_text)
        user_chars = self.normalize_string(submitted_text)

        max_len = max(len(answer_chars), len(user_chars))
        user_chars += [""] * (max_len - len(user_chars))

        match_num = 0
        guessable = 0
        for i in range(max_len):
            if self.is_guessable_letter(answer_chars[i]):
                guessable += 1
                if answer_chars[i] == user_chars[i]:
                    match_num += 1

        if guessable == 0:
            return 0

        percent_correct = match_num / guessable
        base_score = self.INITIAL_SCORE

        # Default to full credit unless a hint modifier is present
        if item_id in self.modifiers:
            deduction = float(self.modifiers[item_id])
            score = base_score * percent_correct * ((100 - deduction) / 100)
            print(f"[MOD] Deducting {deduction}% from question {item_id}")
        else:
            score = base_score * percent_correct

        print(f"Score for question {item_id}: {score} (matches {match_num}/{guessable})")
        return score



    def normalize_string(self, string_val: str):
        return list(string_val.lower())

    def is_guessable_letter(self, char: str) -> bool:
        return char.isalpha() or char.isdigit()

    def get_ss_answer(self, log, question):
        correct_text = question["answers"][0]["text"]
        submitted_text = log.text if hasattr(log, "text") else log["text"]
        answer_chars = self.normalize_string(correct_text)
        submitted_chars = self.normalize_string(submitted_text)
        max_len = max(len(answer_chars), len(submitted_chars))
        if len(submitted_chars) < max_len:
            submitted_chars += [" "] * (max_len - len(submitted_chars))
        for i in range(max_len):
            if i < len(answer_chars) and self.is_guessable_letter(answer_chars[i]):
                if i < len(submitted_chars) and submitted_chars[i] == ' ':
                    submitted_chars[i] = '_'
        return "".join(submitted_chars)

    def get_feedback(self, log, answers):
        for ans in answers:
            if "options" in ans and "feedback" in ans["options"]:
                return ans["options"]["feedback"]
        return None

    def get_overview_items(self):
        overview = []
        if self.hint_deductions < 0:
            overview.append({"message": "Hint Deductions", "value": self.hint_deductions})
        overview.append({"message": "Points Lost", "value": self.points_lost})
        overview.append({"message": "Final Score", "value": self.calculated_percent})
        return overview

