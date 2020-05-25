# Create your views here.
# -*- coding: utf-8 -*-
from Quizz.requests.request_possible_answer import get_possible_answer_of_a_question
from Quizz.requests.request_form import *


def get_user_answers_of_a_player(player):
    return UserAnswers.objects.filter(player=player)


def user_selected_possible_answer(possible_answer, player):
    return len(UserAnswers.objects.filter(possible_answer=possible_answer, player=player)) > 0


def get_input_response_by_question_by_player(question, player):
    possible_answer = get_possible_answer_of_a_question(question)[0]
    return UserAnswers.objects.get(possible_answer=possible_answer, player=player)