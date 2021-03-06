from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.template.loader import get_template
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib import auth
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.encoding import force_text, force_bytes, DjangoUnicodeDecodeError
from .utils import generate_token
from .chiffrer_password import coder_mdp
from .models import Equipe, Participant
from .forms import RegisterForm

def connexion(request):

    # Pour les resultats
    #return redirect('accueil')

    if request.user.is_authenticated:
        return redirect('participant:profile',username=request.user.username)

    context = {
        'data': request.POST,
        'has_error': False
    }
    if request.method == 'POST':
        login = request.POST.get('login')
        password = request.POST.get('password')

        mdp = coder_mdp(password)

        user = auth.authenticate(username=login, password=mdp)

        if user is not None:
            auth.login(request, user)
            return redirect('accueil')
        else:
            messages.add_message(request, messages.ERROR,
                                 "Nom d'utilisateur ou mot de passe incorrect")
            context['has_error'] = True

        if context['has_error']:
            return render(request, 'participant/connexion.html', context)

    return render(request, 'participant/connexion.html')

def inscription(request):

    if request.user.is_authenticated:
        return redirect('participant:profile',username=request.user.username)

    form = RegisterForm(request.POST or None)

    if form.is_valid():

        data = form.cleaned_data

        data['password_equipe'] = coder_mdp(data['password_equipe'])

       # enregistrer l'équipe
        equipe = Equipe.objects.create(nom=data['nom_equipe'], password= data['password_equipe'], niveau=data['niveau'])
        equipe.chef = "{} {}".format(data['nomchef'], data['prenomchef'])

         # enregistrer le chef de l'équipe
        chef_equipe = User.objects.create_user(username=data['nom_user_chef'], email=data['emailchef'])
        chef_equipe.set_password(data['password_equipe'])
        chef_equipe.first_name = data['prenomchef']
        chef_equipe.last_name = data['nomchef']
        chef_equipe.is_active = True


        # enregistrer le coéquipier 1
        coep1 = User.objects.create_user(username=data['nom_user_coep1'], email='')
        coep1.set_password(data['password_equipe'])
        coep1.first_name = data['prenomcoep1']
        coep1.last_name = data['nomcoep1']
        coep1.is_active = True

        # enregistrer le coéquipier 2
        coep2 = User.objects.create_user(username=data['nom_user_coep2'], email='')
        coep2.set_password(data['password_equipe'])
        coep2.first_name = data['prenomcoep2']
        coep2.last_name = data['nomcoep2']
        coep2.is_active = True
    
        # attribution des equipes
        chef_equipe.save()

        coep1.save()
        coep2.save()
        equipe.save()

        liste_participant = [(chef_equipe, data['numerochef'],True), (coep1, '',False), (coep2, '',False)]

        for user, numero, is_chef in liste_participant:
            participant = Participant.objects.create(user=user, numero=numero, equipe=equipe,is_chief=is_chef)
            participant.save()

        """
        current_site = get_current_site(request)
        email_subject = 'Activer votre Equipe'
        message = render_to_string('auth/activate.html',
                               {
                                   'user': chef_equipe,
                                   'domain': current_site.domain,
                                   'uid': urlsafe_base64_encode(force_bytes(chef_equipe.pk)),
                                   'token': generate_token.make_token(chef_equipe)

                               })
        email_message = EmailMessage(
            email_subject,
            message,
            settings.EMAIL_HOST_USER,
            [data['emailchef']]
        )
        email_message.send()
        """

        messages.add_message(request, messages.SUCCESS,"Votre équipe a bien été inscrite. Connectez vous pour connaitre vos numéros participant.")

        return redirect('participant:connexion')


    return render(request, 'participant/inscription.html',{'form':form})


def activate_compte(request, uidb64, token):

    if request.user.is_authenticated:
        return redirect('participant:profile',username=request.user.username)

    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        chef_equipe = User.objects.get(pk=uid)
    except Exception as identifier:
        chef_equipe = None

    if chef_equipe is not None and generate_token.check_token(chef_equipe, token):
        chef_equipe.is_active = True
        chef_equipe.save()
        participants = chef_equipe.participant.equipe.participants.all()
        for participant in participants:
            participant.user.is_active = True
            participant.user.save()
            
        messages.add_message(request, messages.SUCCESS,"Le compte de votre équipe a bien été activé.")

        return redirect('participant:connexion')

    return render(request, 'auth/activate_failed.html')


@login_required(login_url="participant:connexion")
def profile(request, username):


    if request.user.is_staff:
        return redirect('organisateur:accueil')

    user = get_object_or_404(User, username=username)

    equipe = user.participant.equipe

    participants = equipe.participants.all

    return render(request, 'participant/profile.html', locals())

