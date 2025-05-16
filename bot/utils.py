
import math


def change_rank(user_rank: float,
                question_rank: float,
                result: bool
                ) -> tuple[float, float]:
    k = 5.0
    alpha = 0.1

    p_user = 1 / (1 + math.exp(k * (question_rank - user_rank)))

    tmp = int(result)

    user_diff = alpha * (tmp - p_user) * user_rank * (1 - user_rank)
    question_diff = alpha * (p_user - tmp) * \
        question_rank * (1 - question_rank)

    return user_diff, question_diff


def convert_rank(rank: float
                 ) -> int:
    return int(rank*1000)



