# Create your views here.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponseRedirect

# Create your views here.

# ACCES MODEL
from .forms import *

# Import requests
from Quizz.requests.request_user import *
from Quizz.requests.request_form import *
from Quizz.requests.request_question import *
from Quizz.requests.request_game import *
from Quizz.requests.request_possible_answer import *
from Quizz.requests.request_answer_type import *
from Quizz.requests.request_player import *
from Quizz.requests.request_categories import *

# regex
import re
# FOR JSON RESPONSE
from django.http import JsonResponse
from django.core import serializers
# JSON
import json
# OS lib
import os
# settings
from django.conf import settings
# date
import datetime


def index(request):
    user = None
    if 'login' in request.session:
        user = getUserByLogin(request.session['login'])
    allforms = getAllForms(user)

    return render(request, "home/index.html", {'allforms': allforms})


def quizz_by_cat(request, cat_id):
    user = None
    if 'login' in request.session:
        user = getUserByLogin(request.session['login'])
    cat = get_category_by_id(cat_id)
    allforms = getQuizzByCat(cat, user)

    allgames = []
    for f in allforms:
        games = getGamesToJoinByForm(f)
        for g in games:
            if get_nb_player_by_game(g) < g.slot_max:
                allgames.append(g)

    return render(request, "home/quizz_by_cat.html", {'allforms': allforms, 'allgames': allgames, 'cat': cat})


def create_game(request, id_form):
    if 'login' not in request.session:
        return index(request)
    user = getUserByLogin(request.session['login'])
    f = getFormById(id_form)
    questions = getQuestionsByForm(f)
    f.questions = getPossibleAnswersByQuestions(questions)
    game = create_gameBD(f.id, user.login, "Partie de "+user.login, False, 1, False, False, "DRAFT")
    if not is_user_in_game(user, game):
        create_player(game, user)

    return render(request, "home/create-game.html", {'form': f, 'game':game})


def create_game_random(request, cat_id):
    if 'login' not in request.session:
        return index(request)
    user = getUserByLogin(request.session['login'])
    cat = get_category_by_id(cat_id)
    f = get_random_forms_by_cat(cat, user)
    questions = getQuestionsByForm(f)
    f.questions = getPossibleAnswersByQuestions(questions)
    game = create_gameBD(f.id, user.login, "Partie de "+user.login, False, 1, False, True, "DRAFT")
    if not is_user_in_game(user, game):
        create_player(game, user)

    return render(request, "home/create-game.html", {'form': f, 'game':game, 'cat':cat})


def attente(request, game_uuid):
    if 'login' not in request.session:
        return index(request)

    user = getUserByLogin(request.session['login'])
    game_name = request.POST.get('game_name', None)
    slot_max = request.POST.get('slot_max', None)
    is_public = True if request.POST.get('is_public', None) == "on" else False
    is_real_time = True if request.POST.get('is_real_time', None) == "on" else False
    is_limited_time = True if request.POST.get('chk_limited_time', None) == "on" else False
    timer = 0
    if is_limited_time:
        timer = request.POST.get('time_limit', None)
    game = get_game_by_uuid(game_uuid)

    if game.game_status.type=="DRAFT":
        game = edit_game(game_uuid, game_name, slot_max, is_public, is_real_time, is_limited_time, timer, "WAITING")

    if game.is_real_time and game.game_status.type=="IN_PROGRESS":
        return openform(request, game.uuid)

    friends = get_users_friends_not_in_game(user, game)
    for f in friends:
        if is_user_in_waiting_room(game, f) or is_user_invited_in_game(f, game):
            f.is_invited = True
    players = get_players_number_of_game(get_players_by_game(game))
    is_author = game.author == user
    waiting_players = get_players_waiting_by_game(game)

    return render(request, "home/attente.html",
                  {'game':game,
                   'is_author':is_author,
                   'players':players,
                   'friends':friends,
                   'waiting_players':waiting_players})


def joindre_partie(request, game_uuid):
    if 'login' not in request.session:
        return index(request)
    user = getUserByLogin(request.session['login'])
    game = get_game_by_uuid(game_uuid)
    if not is_user_in_game(user, game) and game.slot_max <= len(get_players_by_game(game)):
        # TODO afficher un message de redirection vers les parties en cours lorsque la partie est pleine
        return game_progress(request)

    if is_user_invited_in_game(user, game):
        player = get_player_by_game_by_login(game, user.login)
        player.is_invited = False
        player.save()
    if not is_user_in_game(user, game):
        create_player(game, user)

    if game.is_real_time and game.game_status.type=="IN_PROGRESS":
        return openform(request, game.uuid)

    friends = get_users_friends_not_in_game(user, game)
    for f in friends:
        if is_user_in_waiting_room(game, f) or is_user_invited_in_game(f, game):
            f.is_invited = True
    players = get_players_number_of_game(get_players_by_game(game))
    is_author = game.author == user
    waiting_players = get_players_waiting_by_game(game)

    return render(request, "home/attente.html", {
        'game': game,
        'is_author': is_author,
        'players': players,
        'friends': friends,
       'waiting_players':waiting_players})


def quitter_partie(request, game_uuid):
    if 'login' not in request.session:
        return index(request)
    user = getUserByLogin(request.session['login'])
    game = get_game_by_uuid(game_uuid)
    user_leave_game(user, game)
    return index(request)


def openform(request, game_uuid):
    if 'login' not in request.session:
        return index(request)
    game = get_game_by_uuid(game_uuid)
    login = request.session['login']
    player = get_player_by_game_by_login(game, login)
    if player.score != 0:
        return correction(request, player.id)

    f = getFormById(game.form.id)
    nbQuestions = getNbQuestionsByForm(f)
    if game.is_real_time:
        question = getNextQuestion(game.form, game.actual_question)
        if question != False:
            f.questions = getPossibleAnswersByQuestion(question)
        else:
            f.questions = []
    else:
        questions = getQuestionsByForm(f)
        f.questions = getPossibleAnswersByQuestions(questions)
    kick_invited_players(game)
    if game.game_status.type == "WAITING":
        change_game_status(game, "IN_PROGRESS")
    if game.time_launched is None:
        set_game_time_launch_to_now(game)
        game = get_game_by_uuid(game_uuid)
        game.date_limite = game.time_launched + game.timer
        game.timer_sec = str((game.date_limite - game.time_launched).total_seconds()*1000)
        game.date_limite = str(game.date_limite)
    else:
        game = get_game_by_uuid(game_uuid)
        game.date_limite = game.time_launched + game.timer
        game.timer_sec = str((game.date_limite - game.time_launched).total_seconds()*1000)
        game.date_limite = str(game.date_limite)


    return render(request, "home/game.html",
                  {'form': f,
                   'player': player,
                   'game': game,
                   'nbQuestions':nbQuestions})


def users(request):
    users = getAllUsers()

    return render(request, "home/users.html", {'users': users})


def create_user(request):
    login = request.POST.get('loginco', None)
    email = request.POST.get('emailco', None)
    password = request.POST.get('passwordco', None)
    password_validation = request.POST.get('passwordco2', None)

    if loginExist(login):

        data = {
            'is_valid': False,
            'error_message': "Le pseudo existe déjà."
        }

    elif emailExist(email):

        data = {
            'is_valid': False,
            'error_message': "L'email existe déjà."
        }

    elif password != password_validation:

        data = {
            'is_valid': False,
            'error_message': "Le mot de passe de confirmation est différent."
        }

    else:

        createUserBD(login, email, password)

        data = {
            'is_valid': True,
        }

    return JsonResponse(data)


def connectUser(request):
    login = request.POST.get('login', None)
    password = request.POST.get('password', None)

    if loginExist(login):

        if valideUser(login, password):

            data = {
                'is_valid': True,
            }

            request.session['login'] = login

        else:

            data = {
                'is_valid': False,
                'error_message': "Le mot de passe est incorrect."
            }

    else:

        data = {
            'is_valid': False,
            'error_message': "Le pseudo n'existe pas."
        }

    return JsonResponse(data)


def disconnect(request):
    del request.session['login']

    data = {
        'is_valid': True
    }

    return JsonResponse(data)


def creation(request):
    if 'login' not in request.session:
        return index(request)
    if request.method == 'POST':
        title = request.POST.get('form_title')
        description = request.POST.get('form_description')
        author = getUserByLogin(request.session['login'])
        is_public = request.POST.get('is_public') is not None
        categories = request.POST.get('category_list').split(';')
        if '' in categories: categories.remove('')
        form = addQuizzForm(title, author, description, categories, is_public)
        if request.POST.get('formId') is not None:
            old_form = getFormById(request.POST.get('formId'))
            form.author = old_form.author
            form.save()
            transfer_old_form_right_to_another(old_form, form)
            set_form_old(old_form)

        nbQuestions = request.POST.get('nbQuestions')
        for i in range(int(nbQuestions)):
            numq = i + 1
            numq = str(numq)

            q_title = request.POST.get('qst_' + numq + '_title')
            q_answerType = request.POST.get('qst_' + numq + '_answerType')
            if q_answerType == "radio":
                q_answerType = "UNIQUE_ANSWER"
            elif q_answerType == "checkbox":
                q_answerType = "QCM"
            elif q_answerType == "text":
                q_answerType = "INPUT"
            q_order = request.POST.get('qst_' + numq + '_order')

            type = getType(q_answerType)
            question = addQuestion(form, type, q_title, q_order)

            q_nbAnswers = request.POST.get('qst_' + numq + '_nbAnswers')

            for j in range(int(q_nbAnswers)):
                numa = str(j + 1)
                numa = str(numa)

                a_value = request.POST.get('qst_' + numq + '_ans_' + numa + '_value')
                if q_answerType == "INPUT":
                    a_correct = True
                else:
                    a_correct = request.POST.get('qst_' + numq + '_ans_' + numa + '_correct')
                    a_correct = True if a_correct == 'on' else False

                addPossibleAnswer(question, a_correct, a_value)

        return index(request)

    categories = get_categories()
    data={
        'categories' : categories,
    }

    return render(request, "home/creation.html", data)


def edit_quizz(request, id_quizz):
    
    f = getFormById(id_quizz)
    questions = getQuestionsByForm(f)
    f.questions = getPossibleAnswersByQuestions(questions)
    categories = get_categories()
    
    data={
        'form' : f,
        'categories' : categories,
    }

    return render(request, "home/creation.html", data)


def delete_quizz(request, id_quizz):

    delete_form(id_quizz)

    return index(request)

def edit_right(request, id_quizz):
    form = getFormById(id_quizz)
    if request.method == 'POST':
        is_public = True if request.POST.get('is_public', None) == "on" else False
        set_form_publicity(form, is_public)
        for key, value in request.POST.items():
            if "role" in key:
                id_user = key.split("_")[1]
                role = value
                user = get_user_by_id(id_user)
                if role == "NONE":
                    remove_access_form_for_a_user(user, form)
                else:
                    set_access_form_for_a_user(user, form, role)
    user = getUserByLogin(request.session['login'])
    friends = get_users_friends(user)
    for f in friends:
        f.role_none = False
        f.role_publisher = False
        f.role_editor = False
        if str(user_form_right(f, form, False)) == "NONE":
            f.role_none = True
        elif user_form_right(f, form, False).access_form_type.type == "PUBLISHER":
            f.role_publisher = True
        elif user_form_right(f, form, False).access_form_type.type == "EDITOR":
            f.role_editor = True

    return render(request, "home/edit_right.html", {'form':form, 'friends':friends})


def resultats(request, game_uuid):
    if 'login' not in request.session:
        return index(request)
    game = get_game_by_uuid(game_uuid)
    end_game_limited_time(game)
    players = get_players_by_game_order_by_score_desc(game)
    return render(request, "home/resultats.html", {'game': game, 'players': players})


def game_progress(request):
    if 'login' not in request.session:
        return index(request)
    user = getUserByLogin(request.session['login'])
    invited_games = get_games_invited_of_user(user)
    in_progress_game = get_games_in_progress_of_user(user)
    for in_prog_g in in_progress_game:
        end_game_limited_time(in_prog_g)
    in_progress_game = get_games_in_progress_of_user(user)
    waiting_games = get_waiting_games(user)
    return render(request, "dashboard/game_progress.html",
                  {'active': 4,
                  'invited_games': invited_games,
                   'in_progress_game': in_progress_game,
                   'waiting_games':waiting_games})


def saveUserAnswers(request):
    idplayer = request.POST.get('idplayer')
    player = Player.objects.get(id=idplayer)

    idPA = request.POST.get('idPA')
    valueUser = request.POST.get('value')

    pa = PossibleAnswer.objects.get(id=idPA)
    if pa.question.answer_type.type == "QCM" or pa.question.answer_type.type == "INPUT":
        ua = UserAnswers.objects.filter(player=player, possible_answer=pa)
        if ua.count() >= 1:
            ua = UserAnswers.objects.get(player=player, possible_answer=pa)
            ua.value = valueUser
        else:
            ua = UserAnswers()
            ua.player = player
            ua.possible_answer = pa
            ua.value = valueUser

        ua.save()


    elif pa.question.answer_type.type == "UNIQUE_ANSWER":

        answers = PossibleAnswer.objects.filter(question=pa.question)

        for a in answers:
            ua = UserAnswers.objects.filter(player=player, possible_answer=a)
            if ua.count() >= 1:
                ua = UserAnswers.objects.get(player=player, possible_answer=a)
                ua.delete()

        ua = UserAnswers()
        ua.player = player
        ua.possible_answer = pa
        ua.value = valueUser
        ua.save()

    data = {
        'is_valid': True
    }

    return JsonResponse(data)


def change_user_invite(request):
    user_source = getUserByLogin(request.session['login'])
    user_target_login = request.POST.get('user_target')
    list_users = []
    for user in get_n_first_users_like_with_a_user_to_exclude(user_target_login, user_source):
        list_users.append(user.login)

    data = {
        'is_valid': True,
        'users': list_users
    }
    return JsonResponse(data)


def answer_friend_request(request):
    user_target = getUserByLogin(request.session['login'])
    is_accepted = request.POST.get('request_answer') == "accept"
    user_source = getUserByLogin(request.POST.get('user_source_login'))
    answer_friendship_request(is_accepted, user_source, user_target)

    data = {
        'is_valid': True
    }
    return JsonResponse(data)


def remove_friend(request):
    user_source = getUserByLogin(request.session['login'])
    user_target = getUserByLogin(request.POST.get('user_target_login'))
    remove_friendship(user_source, user_target)

    data = {
        'is_valid': True
    }
    return JsonResponse(data)


def add_friend(request):
    user_source = getUserByLogin(request.session['login'])
    user_target_login = request.POST.get('user_target')
    data = {}
    if not loginExist(user_target_login):
        data.update({'is_valid_login': False})
        return JsonResponse(data)
    if user_target_login == user_source.login:
        data.update({'cant_invite_himself': True})
        return JsonResponse(data)
    data.update({'is_valid_login': True, 'cant_invite_himself':False})
    user_target = getUserByLogin(user_target_login)

    if two_users_have_relationship(user_source, user_target):
        data.update({'relationship_already_established': True})
        data.update({'accepted': relationship_accepted(user_source, user_target)})
        return JsonResponse(data)
    data.update({'relationship_already_established': False})

    add_friend_request(user_source, user_target)

    return JsonResponse(data)


def invite_friend(request):
    user = get_user_by_id(request.POST.get('friend_id'))
    game = get_game_by_uuid(request.POST.get('game_uuid'))

    if is_user_in_waiting_room(game, user) or is_user_invited_in_game(user, game):
        data = {'is_valid': False,
                'message':"La personne a déjà été invité dans la partie.",
                }
        return JsonResponse(data)

    elif game.is_real_time and game.slot_max <= get_nb_player_invited_or_not_by_game(game) :

        data = {'is_valid': False,
                'message':"Vous avez atteind le nombre maximal d'invités pour cette partie.",
                }
        return JsonResponse(data)

    create_player(game, user, True);
    data = {'is_valid': True,
            'message':'L\'inviation a été envoyée avec succès !'}

    return JsonResponse(data)


def kick_user(request):
    user = get_user_by_id(request.POST.get('user_id'))
    game = get_game_by_uuid(request.POST.get('game_uuid'))
    user_leave_game(user, game)

    data = {'is_valid': True}

    return JsonResponse(data)


def correction_question(request):
    question = get_question_by_id(request.POST.get('question_id'))
    need_correction_for_question(question)

    data = {'is_valid': True}

    return JsonResponse(data)


def refuse_game_invitation(request):
    user = getUserByLogin(request.session['login'])
    game = get_game_by_id(request.POST.get('game_id'))
    user_leave_game(user, game)

    data = {'is_valid': True}

    return JsonResponse(data)

def user_profil(request):
    if 'login' not in request.session:
        return index(request)
    user = getUserByLogin(request.session['login'])

    return render(request, 'dashboard/profil.html', {'user': user})
    if request.method == "POST":

        if request.POST.get('newpwd') == '':

            user = editUserWithoutPwd(user.id, request.POST.get('loginedit'), request.POST.get('emailedit'))

        elif request.POST.get('newpwd') == request.POST.get('newpwd2'):

            if valideUser(user.login, request.POST.get('oldPwd')):

                user = editUserBD(user.id, request.POST.get('loginedit'), request.POST.get('emailedit'), request.POST.get('newpwd'))

            else :

                return render(request, 'dashboard/profil.html', {'user': user, 'active': 0, 'invalid_old_pwd': True, 'invalid_new_pwd': False})

        else :

            return render(request, 'dashboard/profil.html', {'user': user, 'active': 0, 'invalid_old_pwd': False, 'invalid_new_pwd': True})

    return render(request, 'dashboard/profil.html', {'user':user, 'active': 0, 'invalid_old_pwd': False, 'invalid_new_pwd': False})


def user_history(request):

    user = getUserByLogin(request.session['login'])

    players = get_players_by_user_desc_date_game(user)

    return render(request, 'dashboard/history.html', {'active': 1, 'players': players})


def correction(request, player_id):
    player = get_player_by_id(player_id)
    game = player.game
    if player.game.is_real_time :
        recalculate_user_answers(player)
        change_game_status(game, "DONE")
    calculate_score(player)
    end_game_limited_time(game)
    questions = getUserAnswersByQuestions(getQuestionsByForm(game.form), player)

    return render(request, 'home/correction.html', {'game': game, 'player': player, 'questions':questions})


def menuCategories(request):
    user = None
    if 'login' in request.session:
        user = getUserByLogin(request.session['login'])
    cats = []
    categories = get_categories()
    for c in categories:
        if nbQuizzByCat(c, user) > 0:
            cats.append({'id': c.id,'label': c.label,'nbQuizz': nbQuizzByCat(c, user)})

    data = {'cats':cats}
    return JsonResponse(data)


def stats(request):
    if 'login' not in request.session:
        return index(request)
    user = getUserByLogin(request.session['login'])
    parties = get_player_number_of_game(user)
    creator_forms = get_creator_form(user)

    cats = get_categories()
    for c in cats :
        c.parties = get_number_of_parties_player_by_user_and_category(user, c)


    data={
        'active': 2,
        'cats':cats,
        'user':user,
        'parties':parties,
        'creator_forms':creator_forms
    }

    return render(request, 'dashboard/classement.html',data)


def amis(request):
    if 'login' not in request.session:
        return index(request)
    user = getUserByLogin(request.session['login'])
    friends = get_users_friends(user)
    send_request_friends = get_waiting_sent_users_friend(user)
    received_request_friends = get_waiting_received_users_friend(user)

    return render(request, 'dashboard/amis.html', {
        'active': 3,
        'friends': friends,
        'send_request_friends': send_request_friends,
        'received_request_friends': received_request_friends})


def chat(request):
    if 'login' not in request.session:
        return index(request)
    return render(request, 'chat/index.html')

def room(request, room_name):
    if 'login' not in request.session:
        return index(request)
    return render(request, 'chat/room.html', {
        'room_name': room_name
    })

def question_answer_by(request):
    num_q = int(request.POST.get('num_row_question'))
    player = get_player_by_id(id=request.POST.get('player'))
    if player.game.actual_question == num_q:
        add_question_to_player(player,request.POST.get('question'))

        game = player.game
        game.actual_question = num_q+1
        game.save()
        data = {'is_valid': True}

    else :
        data = {'is_valid':False}

    return JsonResponse(data)

def handler404(request, exception):
	return render(request, "errors/404.html")

def handler500(request):
	return render(request, "errors/500.html")