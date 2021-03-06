from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes

from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.csrf import csrf_exempt

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout

from django.conf import settings

from django.shortcuts import render, redirect

from textx import metamodel_for_language
from txbibtex import bibfile_str

from .decorators import *

from time import gmtime, strftime
from pathlib import Path

import unidecode
import re
import pprint
import os
import time
import datetime

from .models import Team, Rank, Reference, Project
from .forms import CreateUserForm
from .filters import TeamFilter, ProjectFilter, ReferenceByProjectFilter, ReferenceByRankFilter, ReferenceByTeamFilter, \
    ReferenceByUserFilter, ReferenceFilter, RankFilter


# region Deletion

@login_required(login_url='login')
@is_admin
def deleteRank(request, pk):
    rank = Rank.objects.get(id=pk)
    rank.delete()

    return redirect('/refmng/ranks/')


@login_required(login_url='login')
@belongs_to_user
def deleteTeam(request, pk):
    team = Team.objects.get(id=pk)
    team.delete()

    return redirect('/refmng/teams/')


@login_required(login_url='login')
@belongs_to_user
def deleteReference(request, pk):
    reference = Reference.objects.get(id=pk)
    reference.delete()

    return redirect('/refmng/references/')

@login_required(login_url='login')
@belongs_to_user
def deleteProject(request, pk):
    project = Project.objects.get(id=pk)
    project.delete()

    return redirect('/refmng/projects/')

# endregion Deletion

# region Creation and preview pages

@login_required(login_url='login')
def teamCreationPage(request):
    teams = Team.objects.all()
    users = User.objects.all()

    teamFilter = TeamFilter(request.GET, queryset=teams)
    teams = teamFilter.qs

    pp = pprint.PrettyPrinter(indent=4)
    if (request.method == "POST"):
        if request.POST.get("Create"):
            teamName = request.POST.get("teamName")
            team = Team.objects.create(name=teamName)
            for user in users:
                if request.POST.get("c" + str(user.id)) == "clicked":
                    team.user.add(user)

    users = users.order_by('last_name')
    return render(request, 'teams.html', {"users": users, "teams": teams, "teamFilter": teamFilter})


@login_required(login_url='login')
def projectCreationPage(request):
    projects = Project.objects.all()
    teams = Team.objects.all()

    projectFilter = ProjectFilter(request.GET, queryset=projects)
    projects = projectFilter.qs

    pp = pprint.PrettyPrinter(indent=4)
    if (request.method == "POST"):
        if request.POST.get("Create"):
            projectCode = request.POST.get("projectCode")
            projectTitle = request.POST.get("projectTitle")
            project = Project.objects.create(code=projectCode, title=projectTitle)
            for team in teams:
                if request.POST.get("c" + str(team.id)) == "clicked":
                    project.team.add(team)

    return render(request, 'projects.html', {"projects": projects, "teams": teams, "projectFilter": projectFilter})


@login_required(login_url='login')
def rankCreationPage(request):
    ranks = Rank.objects.all()
    rankFilter = RankFilter(request.GET, queryset=ranks)
    ranks = rankFilter.qs
    pp = pprint.PrettyPrinter(indent=4)
    if (request.method == "POST"):
        if request.POST.get("Create"):
            rankCode = request.POST.get("rankCode")
            Rank.objects.create(code=rankCode)

    return render(request, 'ranks.html', {"ranks": ranks, "rankFilter": rankFilter})

# endregion Creation and preview pages

# region Profile pages

@login_required(login_url='login')
def referenceProfilePage(request, pk):
    reference = Reference.objects.get(id=pk)

    ranks = Rank.objects.all()
    teams = Team.objects.all()
    projects = Project.objects.all()
    users = User.objects.all()

    reference_editors = reference.editor.all()

    authorized = False

    if checkIfUserIsAdmin(request.user) is True or request.user in reference.author.all():
        authorized = True

    if (request.method == "POST"):
        if request.POST.get("update"):
            if authorized is True:
                for key, value in request.POST.items():
                    print(key + ' ' + value)
                    if key not in ['team','project','rank','title','year','isbn','issn', 'doi','key','type','author','editor']:
                        reference = updateAttributes(reference, key, value)
                    else:
                        reference = updateMainFields(reference, key, value)

                #handle editors update
                for user in users:
                    if request.POST.get("c" + str(user.id)) == "clicked":
                        reference.editor.add(user)
                        reference.save
                    else:
                        if user in reference.editor.all():
                            reference.editor.remove(user)
                            reference.save()

            else:
                return redirect('forbidden')


    return render(request, 'referenceProfile.html', {"reference": reference, "ranks": ranks, "teams": teams, "projects": projects, "users": users, "reference_editors": reference_editors})


@login_required(login_url='login')
def teamProfilePage(request, pk):
    team = Team.objects.get(id=pk)
    team_users = team.user.all()
    users = User.objects.all()

    references = Reference.objects.filter(team=team).all()

    reference_count = len(references)

    referenceFilter = ReferenceByTeamFilter(request.GET, queryset=references)
    references = referenceFilter.qs

    authorized = False

    if request.user in team.user.all() or checkIfUserIsAdmin(request.user) is True:
        authorized = True

    if (request.method == "POST"):
        if request.POST.get("export"):
            writeReferencesToFile(references)
        elif request.POST.get("update"):
            if authorized is True:
                for key, value in request.POST.items():
                    print(key + ' ' + value)
                    if key == 'name':
                        setattr(team, key, value)
                        team.save()

                for user in users:
                    if request.POST.get("c" + str(user.id)) == "clicked":
                        team.user.add(user)
                        team.save
                    else:
                        if user in team.user.all():
                            team.user.remove(user)
                            team.save()
            else:
                return redirect('forbidden')



    return render(request, 'teamProfile.html',
                  {"users": users, "team_users": team_users, "team": team, "references": references, "reference_count": reference_count,
                   "referenceFilter": referenceFilter})


@login_required(login_url='login')
def rankProfilePage(request, pk):
    rank = Rank.objects.get(id=pk)

    references = Reference.objects.filter(rank=rank).all()

    reference_count = len(references)

    referenceFilter = ReferenceByRankFilter(request.GET, queryset=references)
    references = referenceFilter.qs

    #only staff can change ranks
    if request.method == "POST":
        if request.POST.get("export"):
            writeReferencesToFile(references)
        elif request.POST.get("update"):
            if checkIfUserIsAdmin(request.user) is True:
                for key, value in request.POST.items():
                    setattr(rank, key, value)
                    rank.save()
            else:
                return redirect('forbidden')

    return render(request, 'rankProfile.html',
                  {"rank": rank, "references": references, "reference_count": reference_count,
                   "referenceFilter": referenceFilter})


@login_required(login_url='login')
def userProfilePage(request, pk):
    pp = pprint.PrettyPrinter(indent=4)
    user = User.objects.get(id=pk)
    allTeams = Team.objects.all()
    teams = []
    references = []
    for team in allTeams:
        if user in team.user.all():
            teams.append(team)

    for reference in Reference.objects.all():
        if user in reference.author.all():
            references.append(reference)

    referenceFilter = ReferenceByTeamFilter(request.GET, queryset=Reference.objects.filter(
        author__username__icontains=user.username))
    references = referenceFilter.qs

    reference_count = len(references)


    authorized = False
    if request.user == user or checkIfUserIsAdmin(request.user) is True:
        authorized = True

    if (request.method == "POST"):
        if request.POST.get("export"):
            writeReferencesToFile(references)
        elif request.POST.get("update"):
            if authorized is True:
                for key, value in request.POST.items():
                    setattr(user, key, value)
                    user.save()
            else:
                return redirect('forbidden')


    return render(request, 'userProfile.html',
                  {"user": user, "teams": teams, "references": references, "reference_count": reference_count,
                   "referenceFilter": referenceFilter})


@login_required(login_url='login')
def projectProfilePage(request, pk):
    project = Project.objects.get(id=pk)

    project_teams = project.team.all()
    teams = Team.objects.all()

    references = []

    referenceFilter = ReferenceByProjectFilter(request.GET, queryset=Reference.objects.filter(project=project))
    references = referenceFilter.qs

    reference_count = len(references)

    authorized = False

    for team in teams:
        if request.user in team.user.all():
            authorized = True
            break

    if checkIfUserIsAdmin(request.user):
        authorized = True

    if (request.method == "POST"):
        if request.POST.get("export"):
            writeReferencesToFile(references)
        elif request.POST.get("update"):
            if authorized is True:
                for key, value in request.POST.items():
                    print(key + ' ' + value)
                    if key in ['title', 'code']:
                        setattr(project, key, value)
                        project.save()
                for team in teams:
                    if request.POST.get("c" + str(team.id)) == "clicked":
                        project.team.add(team)
                        project.save
                    else:
                        if team in project.team.all():
                            project.team.remove(team)
                            project.save()
        else:
            return redirect('forbidden')

    return render(request, 'projectProfile.html',
                  {"project": project, "teams": teams, "project_teams": project_teams, "references": references, "reference_count": reference_count,
                   "referenceFilter": referenceFilter, "authorized": authorized})

# endregion Profile pages

# region Registration and authentication

@unauthenticated_user
def registerPage(request):
    form = CreateUserForm()

    if (request.method == 'POST'):
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')

    context = {'form': form}
    return render(request, 'register.html', context)


@unauthenticated_user
def loginPage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('references')
        else:
            messages.info(request, 'Username OR password is incorrect')

    context = {}
    return render(request, 'login.html', context)


@login_required(login_url='login')
def logoutUser(request):
    logout(request)
    return redirect('login')


def forbidden(request):
    return render(request, 'forbidden.html')

# endregion Registration and authentication

#region References Export

def writeReferencesToFile(references):
    result = ''
    if references:
        for reference in references:
            result += writeReferenceInBibTex(reference)
            result += '\n'

    downloads_path = str(Path.home() / "Downloads")
    title = downloads_path + '\export' + str(strftime("%Y%m%d-%H%M%S", gmtime())) + '.bib'
    print(title)
    f = open(title, "w", encoding="utf-8")
    f.write(result)
    f.close()

    return result


def writeReferenceInBibTex(reference):
    result = ''

    result += ("@" + reference.type)
    result += "{"
    result += (reference.key + ",\n\t")

    if reference.author:
        if len(reference.author.all()) > 0:
            result += "author = {"
            result += writeUsers(reference.author)
            result += "},\n\t"

    if reference.editor:
        if len(reference.editor.all()) > 0:
            result += "editor = {"
            result += writeUsers(reference.editor)
            result += "},\n\t"

    if reference.project:
        result += ("project = {" + reference.project.code + "},\n\t")

    if reference.rank:
        result += ("rank = {" + reference.rank.code + "},\n\t")

    if reference.year != 0:
        result += ("year = {" + str(reference.year) + "},\n\t")

    if reference.isbn != "":
        result += ("isbn = {" + reference.isbn + "},\n\t")

    if reference.issn != "":
        result += ("issn = {" + reference.issn + "},\n\t")

    if reference.doi != "":
        result += ("doi = {" + reference.doi + "},\n\t")

    if reference.title != "":
        result += ("title = {" + reference.title + "},\n\t")


    result += writeAttributes(reference.attributes)


    result += "}\n"

    return result


def writeUsers(users):
    length = len(users.all())
    index = 0
    result = ''

    for user in users.all():
        result += user.first_name + " " + user.last_name
        if index != (length-1):
            result += " and "

        index = index + 1

    return result


def writeAttributes(attributes):
    length = len(attributes.all())
    index = 0
    result = ''

    for attribute in attributes.all():
        if index != (length-1):
            result += attribute.name + " = {" + attribute.value + "},\n\t"
        else:
            result += attribute.name + " = {" + attribute.value + "}\n"

        index = index + 1

    return result

#endregion References Export

# region References Upload

@login_required(login_url='login')
def referenceCreationPage(request):
    context = {}
    pp = pprint.PrettyPrinter(indent=4)

    references = Reference.objects.all()
    reference_count = len(references)
    referenceFilter = ReferenceFilter(request.GET, queryset=references)
    references = referenceFilter.qs

    successful = 0
    unsuccessful = 0
    success_message = ''
    error_message = ''
    export_message = ''

    if request.method == 'POST':

        if request.POST.get("export"):
            print('uso export')
            writeReferencesToFile(references)
            export_message = "References successfully exported to your Downloads folder"
        else:
            try:
                #region Uploaded File Processing
                uploaded_file = request.FILES['document']

                path = default_storage.save(r'tmp\references.bib', ContentFile(uploaded_file.read()))
                path_to_file = default_storage.open(r'tmp\references.bib').name

                bibfile = metamodel_for_language('bibtex').model_from_file(path_to_file)
                #endregion Uploaded File Processing

                #region Entries Processing
                for e in bibfile.entries:
                    if e.__class__.__name__ == 'BibRefEntry':

                        #region Reference Key And Type
                        key = e.key
                        type = e.type
                        #endregion Reference Key And Type

                        # region Field Assigning
                        author_field = getField(e, 'author')
                        title_field = getField(e, 'title')
                        doi_field = getField(e, 'doi')
                        year_field = getField(e, 'year')
                        rank_field = getField(e, 'rank')
                        project_field = getField(e, 'project')

                        editor_field = getField(e, 'editor')
                        isbn_field = getField(e, 'isbn')
                        issn_field = getField(e, 'issn')
                        # endregion Field Assigning

                        # region Value Assigning
                        try:
                            author_value = author_field.value.lstrip().rstrip()
                        except:
                            author_value = ""
                        try:
                            title_value = title_field.value.lstrip().rstrip()
                        except:
                            title_value = ""
                        try:
                            year_value = year_field.value
                        except:
                            year_value = 0
                        try:
                            rank_value = rank_field.value.lstrip().rstrip()
                        except:
                            rank_value = ""
                        try:
                            project_value = project_field.value.lstrip().rstrip()
                        except:
                            project_value = ""
                        try:
                            isbn_value = isbn_field.value.lstrip().rstrip()
                        except:
                            isbn_value = ""
                        try:
                            issn_value = issn_field.value.lstrip().rstrip()
                        except:
                            issn_value = ""
                        try:
                            doi_value = doi_field.value.lstrip().rstrip()
                        except:
                            doi_value = ""
                        try:
                            editor_value = editor_field.value.lstrip().rstrip()
                        except:
                            editor_value = ""
                        # endregion Value Assigning

                        # region Authors Processing
                        # gets list of authors (strings)
                        authors = getUsers(author_field)
                        # trims all strings in a list and writes them to a new list (can't change strings)
                        resulting_authors = trimAllStrings(authors)
                        # finds user objects that have the same combination of first name and last name
                        authors_objects = getUserObjects(resulting_authors)
                        # endregion Authors Processing

                        # region Duplicate Checking
                        # if reference entry is a duplicate, then move on to the next entry
                        if checkIfDuplicate(isbn_value, issn_value, doi_value, authors_objects, title_value) is True:
                            unsuccessful = unsuccessful + 1
                            continue
                        # endregion Duplicate Checking

                        # region Editors Processing
                        # gets list of editors (strings)
                        try:
                            editors = getUsers(editor_field)
                        except:
                            editors = ''

                        # trims all strings in a list and writes them to a new list (can't change strings)
                        resulting_editors = trimAllStrings(editors)
                        # finds user objects that have the same combination of first name and last name
                        editors_objects =getUserObjects(resulting_editors)
                        # endregion Editors Processing

                        # region Rank Processing
                        rank = getRankObject(rank_value)
                        # endregion Rank Processing

                        # region Team Processing
                        team = getTeamObject(authors_objects)
                        # endregion Team Processing

                        # region Project Processing
                        project = getProjectObject(project_value)
                        # endregion Project Processing

                        # region Reference Saving
                        reference = Reference.objects.create(team=team, project=project, rank=rank, title = title_value, year=year_value,
                                                             isbn=isbn_value, issn=issn_value, doi=doi_value, key=key, type=type)
                        successful = successful + 1

                        #saving authors in reference
                        for author_object in authors_objects:
                            reference.author.add(author_object)

                        #saving editors in reference
                        for editor_object in editors_objects:
                            reference.editor.add(editor_object)

                        #saving the rest of the attributes
                        fields = getRefAttrFields(e)
                        if fields:
                            for field in fields:
                                reference_attribute = ReferenceAttribute.objects.create(name=field.name, value=field.value)
                                reference.attributes.add(reference_attribute)

                        # endregion Reference Saving

                        reference_count = len(Reference.objects.all())
            except:
                error_message = 'Chosen file was not in correct format.'
                time.sleep(2)
                path = default_storage.delete(r'tmp\references.bib')
                return render(request, 'references.html',
                              {"references": references, "referenceFilter": referenceFilter,
                               "reference_count": reference_count, "error_message": error_message})

            #endregion Entries Processing

            time.sleep(2)
            path = default_storage.delete(r'tmp\references.bib')

            #region Messages
            if successful > 0:
                if successful == 1:
                    success_message = 'Successfully uploaded ' + str(successful) + ' reference.'
                else:
                    success_message = 'Successfully uploaded ' + str(successful) + ' references.'
            if unsuccessful > 0:
                if unsuccessful == 1:
                    error_message = 'Skipped ' + str(unsuccessful) + ' reference.'
                else:
                    error_message = 'Skipped ' + str(unsuccessful) + ' references.'
            #endregion Messages

            return render(request, 'references.html',
                          {"references": references, "referenceFilter": referenceFilter, "reference_count": reference_count,
                           "success_message": success_message, "error_message": error_message})

    reference_count = len(references)
    references = references.order_by('year')
    return render(request, 'references.html',
                  {"references": references, "referenceFilter": referenceFilter, "reference_count": reference_count, "export_message": export_message})


def getFields(e):
    fields = [f for f in e.fields]
    if fields:
        return fields


def getRefAttrFields(e):
    fields = [f for f in e.fields]
    resulting_fields = []
    if fields:
        for field in fields:
            if field.name not in ['team','project','rank','title','year','isbn','issn', 'doi','key','type','author','editor']:
                resulting_fields.append(field)
        return resulting_fields


# make new list with trimmed names of authors
def trimAllStrings(strings):
    resulting_authors = []
    for author in strings:
        author_without_space = author.lstrip().rstrip()
        resulting_authors.append(author_without_space)

    return resulting_authors


# get list of user objects from names in bib file
def getUserObjects(names):
    users_objects = []
    for res_user in names:
        for db_user in User.objects.all():
            if res_user.lower() == (db_user.first_name + ' ' + db_user.last_name).lower():
                users_objects.append(db_user)

    return users_objects


# get rank object from code in bib file
def getRankObject(rank_name):
    for db_rank in Rank.objects.all():
        if rank_name.lower() == db_rank.code.lower():
            return db_rank

    return None


# get team object from authors in bib file
def getTeamObject(authors_objects):
    for db_team in Team.objects.all():
        if set(authors_objects) == set(db_team.user.all()):
            return db_team
    return None


# get project object from code in bib file
def getProjectObject(project_code):
    for db_project in Project.objects.all():
        if project_code == db_project.code:
            return db_project

    return None


def checkIfDuplicate(isbn, issn, doi, authors, title):
    for db_reference in Reference.objects.all():
        # check if reference with the same isbn, issn or doi already exists
        if isbn.lower().lstrip().rstrip() == db_reference.isbn.lower().lstrip().rstrip() and isbn != '':
            return True
        if issn.lower().lstrip().rstrip() == db_reference.issn.lower().lstrip().rstrip() and issn != '':
            return True
        if doi.lower().lstrip().rstrip() == db_reference.doi.lower().lstrip().rstrip() and doi != '':
            return True

        # check if reference with the same authors and title exists
        if list(authors) == list(db_reference.author.all()) and title.lower() == db_reference.title.lower():
            return True

    return False


def getField(e, name):
    fields = [f for f in e.fields if f.name == name]
    if fields:
        return fields[0]


def getAuthor(f):
    astr = f.value
    if ' and ' in astr:
        astr = astr.split(' and ')[0]
    if ',' in astr:
        astr = astr.split(',')[0]
        astr = astr.replace(' ', '')
    return toKey(astr.split()[0])


def getUsers(f):
    result = []
    astr = f.value
    if 'and ' in astr:
        astr = astr.split('and ')
        result = astr
    else:
        result.append(astr)

    return result


def toKey(k):
    nonkeychars = re.compile('[^a-zA-Z0-9]')
    k = unidecode.unidecode(k.strip().lower())
    k = nonkeychars.sub('', k)
    return k

# endregion References Upload

#region References Update

def updateMainFields(reference, key, value):
    if key in ['title','year', 'key','type']:
        setattr(reference, key, value)
        reference.save()
    elif key == 'team':
        setattr(reference, key, Team.objects.get(id=value))
        reference.save()
    elif key == 'rank':
        setattr(reference, key, Rank.objects.get(code=value))
        reference.save()
    elif key == 'project':
        setattr(reference, key, Project.objects.get(id=value))
        reference.save()

    return reference


def updateAttributes(reference, key, value):
    for attribute in reference.attributes.all():
        if attribute.name == key.rstrip(','):
            attribute.value = value
            attribute.save()
    return reference

#endregion References Update

