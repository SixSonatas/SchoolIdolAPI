# -*- coding: utf-8 -*-
import datetime
from django.shortcuts import get_object_or_404
from django import forms
from django.forms import Form, ModelForm, ModelChoiceField, ChoiceField
from django.contrib.auth.models import User, Group
from django.db.models import Count
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, string_concat, ungettext_lazy
from django.db.models.fields import BLANK_CHOICE_DASH
from django.core.validators import RegexValidator
from django.conf import settings
from api.raw import STARTERS
from web.templatetags.choicesToString import skillsIcons
from web.utils import randomString
from multiupload.fields import MultiFileField
from api import models

class DateInput(forms.DateInput):
    input_type = 'date'

def date_input(field):
    field.widget = DateInput()
    field.widget.attrs.update({
        'class': 'calendar-widget',
        'data-role': 'data',
    })
    return field

class CreateUserForm(ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = User
        fields = ('username', 'email', 'password')

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email')

class AddLinkForm(ModelForm):
    class Meta:
        model = models.UserLink
        fields = ('type', 'value', 'relevance')

class ChangePasswordForm(Form):
    old_password = forms.CharField(widget=forms.PasswordInput(), label=_('Old Password'))
    new_password = forms.CharField(widget=forms.PasswordInput(), label=_('New Password'))
    new_password2 = forms.CharField(widget=forms.PasswordInput(), label=_('New Password Again'))

    def clean(self):
        if ('new_password' in self.cleaned_data and 'new_password2' in self.cleaned_data
            and self.cleaned_data['new_password'] == self.cleaned_data['new_password2']):
            return self.cleaned_data
        raise forms.ValidationError(_("The two password fields did not match."))

def getGirls(with_total=False, with_japanese_name=False):
    return [('', '')] + [(idol['name'], (idol['idol__japanese_name'] if with_japanese_name and idol['idol__japanese_name'] else idol['name']) + (' (' + unicode(idol['total']) + ')' if with_total else '')) for idol in settings.CARDS_INFO['idols']]

class UserPreferencesForm(ModelForm):
    best_girl = ChoiceField(label=_('Best Girl'), choices=[], required=False)

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(UserPreferencesForm, self).__init__(*args, **kwargs)
        self.fields['best_girl'].choices = getGirls(with_japanese_name=(request and request.LANGUAGE_CODE == 'ja'))
        self.fields['birthdate'] = date_input(self.fields['birthdate'])

    class Meta:
        model = models.UserPreferences
        fields = ('color', 'best_girl', 'location', 'birthdate', 'private', 'description', 'private', 'default_tab')

class _AccountForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(_AccountForm, self).__init__(*args, **kwargs)
        self.fields['starter'].queryset = models.Card.objects.filter(pk__in=STARTERS)
        if 'creation' in self.fields:
            self.fields['creation'] = date_input(self.fields['creation'])

    def clean_creation(self):
        if 'creation' in self.cleaned_data:
            if self.cleaned_data['creation']:
                if self.cleaned_data['creation'] < datetime.date(2013, 4, 16):
                    raise forms.ValidationError(_('The game didn\'t even existed at that time.'))
                if self.cleaned_data['creation'] > datetime.date.today():
                    raise forms.ValidationError(_('This date cannot be in the future.'))
            return self.cleaned_data['creation']

class AccountForm(_AccountForm):
    class Meta:
        model = models.Account
        fields = ('nickname', 'language', 'os', 'friend_id', 'rank', 'starter')

def _ownedcard_label(obj):
    return unicode(obj.card) + ' ' + ('idolized' if obj.idolized else '')

class OwnedCardModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return _ownedcard_label(obj)

class FullAccountForm(_AccountForm):
    center = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.filter(pk=0), required=False, label=_('Center'))
    # Always override this queryset to set the current account only
    # form.fields['center'].queryset = models.OwnedCard.objects.filter(owner_account=owned_account, stored='Deck')

    def __init__(self, *args, **kwargs):
        super(FullAccountForm, self).__init__(*args, **kwargs)
        self.fields['default_tab'].choices = [(k, v) for k, v in list(models.ACCOUNT_TAB_CHOICES) if k != 'presentbox']

    class Meta:
        model = models.Account
        fields = ('nickname', 'center', 'rank', 'friend_id', 'show_friend_id', 'language', 'os', 'device', 'default_tab', 'play_with', 'accept_friend_requests', 'starter', 'creation', 'show_creation', 'loveca', 'friend_points', 'g', 'tickets', 'vouchers', 'bought_loveca', 'show_items')

class FullAccountNoFriendIDForm(FullAccountForm):
    class Meta:
        model = models.Account
        fields = ('nickname', 'center', 'rank', 'os', 'device', 'default_tab', 'play_with', 'accept_friend_requests', 'starter', 'creation', 'show_creation', 'show_friend_id', 'loveca', 'friend_points', 'g', 'tickets', 'vouchers', 'bought_loveca', 'show_items')

class SimplePasswordForm(Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'off'}), label=_('Password'))

class ConfirmDelete(forms.Form):
    confirm = forms.BooleanField(required=True, initial=False, label=_('Confirm that you want to delete it.'))
    thing_to_delete = forms.IntegerField(widget=forms.HiddenInput, required=True)

class TransferCodeForm(ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), label=_('Password'))
    confirm = forms.BooleanField(required=True, initial=False, label=_('Delete previously saved transfer code'))
    class Meta:
        model = models.Account
        fields = ('transfer_code',)

class _OwnedCardForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(_OwnedCardForm, self).__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'card'):
            if self.instance.card.is_special or self.instance.card.is_promo:
                self.fields['idolized'].widget = forms.HiddenInput()
        if 'origin' in self.fields:
            self.fields['origin'].required = False

    def save(self, commit=True):
        instance = super(_OwnedCardForm, self).save(commit=False)
        if instance.card.is_special:
            instance.idolized = False
        if instance.card.is_promo:
            instance.idolized = True
        if commit:
            instance.save()
        return instance

class QuickOwnedCardForm(_OwnedCardForm):
    card = forms.IntegerField()
    class Meta:
        model = models.OwnedCard
        fields = ('card', 'owner_account', 'idolized')

class EditQuickOwnedCardForm(_OwnedCardForm):
    card = forms.IntegerField()
    class Meta:
        model = models.OwnedCard
        fields = ('idolized',)

class StaffAddCardForm(ModelForm):
    card = forms.IntegerField()
    owner_account = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        super(StaffAddCardForm, self).__init__(*args, **kwargs)
        self.fields['owner_account'].widget = forms.HiddenInput()

    def save(self, commit=True):
        self.instance.card = get_object_or_404(models.Card, pk=self.cleaned_data['card'])
        self.instance.owner_account = get_object_or_404(models.Account, pk=self.cleaned_data['owner_account'])
        return super(StaffAddCardForm, self).save(commit)

    class Meta:
        model = models.OwnedCard
        fields = ('card', 'owner_account', 'stored', 'idolized', 'max_level', 'max_bond', 'skill')
        exclude = ('card', 'owner_account')

class OwnedCardForm(_OwnedCardForm):
    class Meta:
        model = models.OwnedCard
        fields = ('owner_account', 'stored', 'idolized', 'max_level', 'max_bond', 'skill', 'origin')

class EditOwnedCardForm(_OwnedCardForm):
    class Meta:
        model = models.OwnedCard
        fields = ('stored', 'idolized', 'max_level', 'max_bond', 'skill', 'origin')

def getOwnedCardForm(form, accounts, owned_card=None):
    form.fields['owner_account'].queryset = accounts
    form.fields['owner_account'].required = True
    form.fields['owner_account'].empty_label = None
    if owned_card is not None:
        if not owned_card.card.skill:
            form.fields.pop('skill')
    return form

class EventParticipationForm(ModelForm):
    class Meta:
        model = models.EventParticipation
        fields = ('account', 'ranking', 'points', 'song_ranking')

class EventParticipationNoSongForm(ModelForm):
    class Meta:
        model = models.EventParticipation
        fields = ('account', 'ranking', 'points')

class EventParticipationNoAccountForm(ModelForm):
    class Meta:
        model = models.EventParticipation
        fields = ('ranking', 'points', 'song_ranking')

class EventParticipationNoSongNoAccountForm(ModelForm):
    class Meta:
        model = models.EventParticipation
        fields = ('ranking', 'points')

def getEventParticipationForm(form, accounts):
    form.fields['account'].queryset = accounts
    form.fields['account'].required = True
    form.fields['account'].empty_label = None
    return form

class UserProfileStaffForm(ModelForm):
    class Meta:
        model = models.UserPreferences
        fields = ('status', 'donation_link', 'donation_link_title', 'description', 'location', 'location_changed')

class AccountAdminForm(ModelForm):
    owner_id = forms.IntegerField(required=False)
    center = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=True)
    class Meta:
        model = models.Account
        fields = ('owner_id', 'friend_id', 'verified', 'rank', 'os', 'device', 'default_tab', 'nickname', 'language','play_with', 'accept_friend_requests', 'center')

class AccountStaffForm(ModelForm):
    center = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=True)
    class Meta:
        model = models.Account
        fields = ('friend_id', 'rank', 'center')

class MultiImageField(MultiFileField, forms.ImageField):
    pass

class _Activity(ModelForm):
    def clean_message_data(self):
        if 'message_data' in self.cleaned_data:
            if len(self.cleaned_data['message_data']) > 8000:
                raise forms.ValidationError(
                    message=_('Ensure this value has at most %(max)d characters (it has %(length)d).'),
                    code='max',
                    params={
                        'max': 8000,
                        'length': len(self.cleaned_data['message_data']),
                    })
        return self.cleaned_data['message_data']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        initial = kwargs.get('initial', {})
        initial['right_picture'] = ''
        kwargs['initial'] = initial
        super(_Activity, self).__init__(*args, **kwargs)
        self.fields['right_picture'].help_text = _('Use a valid imgur URL such as http://i.imgur.com/6oHYT4B.png')
        self.fields['right_picture'].label = _('Picture')
        self.fields['right_picture'].validators.append(RegexValidator(
            regex=settings.IMGUR_REGEXP,
            message='Invalid Imgur URL',
            code='invalid_url',
        ))

class EditActivityPicture(_Activity):
    def __init__(self, *args, **kwargs):
        super(EditActivityPicture, self).__init__(*args, **kwargs)
        self.fields['right_picture'].required = True

    class Meta:
        model = models.Activity
        fields = ('right_picture',)

class CustomActivity(_Activity):
    account_id = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        super(CustomActivity, self).__init__(*args, **kwargs)
        self.fields['account_id'].widget = forms.HiddenInput()
        self.fields['message_data'].required = True
        self.fields['message_data'].label = _('Message')
        self.fields['message_data'].help_text = _('Write whatever you want. You can add formatting and links using Markdown.')

    class Meta:
        model = models.Activity
        fields = ('account_id', 'message_data', 'right_picture')

class VerificationRequestForm(ModelForm):
    upload_images = MultiImageField(min_num=0, max_num=10, required=False, help_text=_('If your files are too large, send them one by one. First upload one image, then edit your request with the second one, and so on. If even one image doesn\'t work, please resize your images.'))

    def __init__(self, *args, **kwargs):
        account = None
        if 'account' in kwargs:
            account = kwargs.pop('account')
        super(VerificationRequestForm, self).__init__(*args, **kwargs)
        if account is not None:
            if account.language != 'JP' and account.language != 'EN':
                self.fields['verification'].choices = ((0, ''), (1, _('Silver Verified')))
            elif account.rank < 195:
                self.fields['verification'].choices = ((0, ''), (1, _('Silver Verified')), (2, _('Gold Verified')))

    class Meta:
        model = models.VerificationRequest
        fields = ('verification', 'comment', 'upload_images', 'allow_during_events')

class StaffVerificationRequestForm(ModelForm):
    images = MultiImageField(min_num=0, max_num=10, required=False)
    status = forms.ChoiceField(choices=((3, 'Verified'), (0, 'Rejected')), widget=forms.RadioSelect)

    class Meta:
        model = models.VerificationRequest
        fields = ('status', 'verification_comment', 'images')

class StaffFilterVerificationRequestForm(ModelForm):
    OS = forms.ChoiceField(choices=BLANK_CHOICE_DASH + list(models.OS_CHOICES), required=False)
    language = forms.ChoiceField(choices=BLANK_CHOICE_DASH + list(models.LANGUAGE_CHOICES), required=False)

    def __init__(self, *args, **kwargs):
        super(StaffFilterVerificationRequestForm, self).__init__(*args, **kwargs)
        self.fields['verified_by'].queryset = User.objects.filter(is_staff=True)
        self.fields['verified_by'].required = False
        self.fields['status'].required = False
        self.fields['status'].choices = BLANK_CHOICE_DASH + self.fields['status'].choices
        self.fields['verification'].required = False
        self.fields['verification'].help_text = None
        self.fields['allow_during_events'].help_text = None
        self.fields['allow_during_events'].label = 'Allowed us to verify them during events'

    class Meta:
        model = models.VerificationRequest
        fields = ('status', 'verified_by', 'verification', 'OS', 'language', 'allow_during_events')

class ModerationReportForm(ModelForm):
    images = MultiImageField(min_num=0, max_num=10, required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.account = kwargs.pop('account', None)
        self.eventparticipation = kwargs.pop('eventparticipation', None)
        self.user = kwargs.pop('user', None)
        self.activity = kwargs.pop('activity', None)
        super(ModerationReportForm, self).__init__(*args, **kwargs)

    def save(self):
        instance = super(ModerationReportForm, self).save(commit=False)
        instance.status = 1
        if self.request.user.is_authenticated():
            instance.reported_by = self.request.user
        if self.account is not None:
            instance.fake_account = self.account
        elif self.eventparticipation is not None:
            instance.fake_eventparticipation = self.eventparticipation
        elif self.user is not None:
            instance.fake_user = self.user
        elif self.activity is not None:
            instance.fake_activity = self.activity
        instance.save()
        for image in self.cleaned_data['images']:
            imageObject = models.UserImage.objects.create()
            imageObject.image.save(randomString(64), image)
            instance.images.add(imageObject)
        return instance

    class Meta:
        model = models.ModerationReport
        fields = ('comment', 'images')

class StaffEnglishBannerForm(ModelForm):
    event = forms.ModelChoiceField(queryset=models.Event.objects.filter(english_beginning__isnull=False).order_by('-english_beginning'))
    class Meta:
        model = models.Event
        fields = ('event', 'english_image',)

class FilterSongForm(ModelForm):
    search = forms.CharField(required=False, label=_('Search'))
    ordering = forms.ChoiceField(choices=[
        ('id', _('Date added')),
        ('latest', _('Latest unlocked songs')),
        ('name', _('Song name')),
        ('BPM', _('Beats per minute')),
        ('time', _('Song length')),
        ('rank', _('Rank to unlock song')),
        ('hard_notes', _('Notes in Hard song')),
        ('expert_notes', _('Notes in Expert song')),
        ('master_notes', _('Notes in Master song')),
    ], initial='id', required=False, label=_('Ordering'))
    reverse_order = forms.BooleanField(initial=True, required=False, label=_('Reverse order'))
    is_daily_rotation = forms.NullBooleanField(required=False, label=_('Daily rotation'))
    is_event = forms.NullBooleanField(required=False, label=_('Event'))
    main_unit = forms.ChoiceField(choices=[
        ('', ''),
        ('μ\'s', 'μ\'s'),
        ('Aqours', 'Aqours'),
    ], required=False, label=_('Main Unit'))
    available = forms.NullBooleanField(required=False, label=_('Available'))

    def __init__(self, *args, **kwargs):
        super(FilterSongForm, self).__init__(*args, **kwargs)
        for field in self.fields.keys():
            self.fields[field].widget.attrs['placeholder'] = self.fields[field].label

    class Meta:
        model = models.Song
        fields = ('search', 'attribute', 'is_daily_rotation', 'is_event', 'available', 'ordering', 'reverse_order')

class FilterEventForm(ModelForm):
    search = forms.CharField(required=False, label=_('Search'))

    is_world = forms.BooleanField(required=False, label=_('Worldwide only'))
    event_type = forms.ChoiceField(label=_('Type'), choices=BLANK_CHOICE_DASH + [
        ('Token', _('Token/Diary')),
        ('Score Match', 'Score Match'),
        ('Challenge Festival', _('Challenge Festival')),
        ('Medley Festival', 'Medley Festival'),
    ])
    idol = ChoiceField(label=_('Idol'), choices=[], required=False)
    idol_attribute = forms.ChoiceField(choices=[], label=string_concat(_('Super Rare'), ': ', _('Attribute')), required=False)
    idol_skill = forms.ChoiceField(choices=(BLANK_CHOICE_DASH + [
        ('Perfect Lock', 'Perfect Lock'),
        ('Score Up', 'Score Up'),
    ]), label=string_concat(_('Super Rare'), ': ', _('Skill')), required=False)
    participation = forms.NullBooleanField(required=False, label=_('I participated'))

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(FilterEventForm, self).__init__(*args, **kwargs)
        self.fields['idol'].choices = getGirls(with_japanese_name=(request and request.LANGUAGE_CODE == 'ja'))
        attributes = list(models.ATTRIBUTE_CHOICES)
        del(attributes[-1])
        self.fields['idol_attribute'].choices = BLANK_CHOICE_DASH + attributes
        if not request or not request.user.is_authenticated():
            del(self.fields['participation'])

    class Meta:
        model = models.Event
        fields = ('search', 'is_world', 'event_type', 'idol', 'idol_attribute', 'idol_skill')

class FilterUserForm(ModelForm):
    search = forms.CharField(required=False, label=_('Search'))
    id_search = forms.IntegerField(required=False, label=_('Friend ID'))
    ordering = forms.ChoiceField(choices=[
        ('rank', _('Leaderboard')),
        ('owner__date_joined', _('New players')),
    ], initial='latest', required=False, label=_('Ordering'))
    reverse_order = forms.BooleanField(initial=True, required=False, label=_('Reverse order'))

    attribute = forms.ChoiceField(choices=(BLANK_CHOICE_DASH + list(models.ATTRIBUTE_CHOICES)), label=_('Attribute'), required=False)
    best_girl = ChoiceField(label=_('Best Girl'), choices=[], required=False)
    # location = forms.CharField(required=False, label=_('Location'))
    private = forms.NullBooleanField(required=False, label=_('Private Profile'))
    status = ChoiceField(label=_('Donators'), choices=(BLANK_CHOICE_DASH + list(models.STATUS_CHOICES)), required=False)
    with_friend_id = forms.NullBooleanField(required=True, label=string_concat(_('Friend ID'), ' (', _('specified'), ')'))
    center_attribute = forms.ChoiceField(choices=(BLANK_CHOICE_DASH + list(models.ATTRIBUTE_CHOICES)), label=string_concat(_('Center'), ': ', _('Attribute')), required=False)
    center_rarity = forms.ChoiceField(choices=(BLANK_CHOICE_DASH + list(models.RARITY_CHOICES)), label=string_concat(_('Center'), ': ', _('Rarity')), required=False)

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(FilterUserForm, self).__init__(*args, **kwargs)
        for field in self.fields.keys():
            self.fields[field].widget.attrs['placeholder'] = self.fields[field].label
        self.fields['best_girl'].choices = getGirls(with_japanese_name=(request and request.LANGUAGE_CODE == 'ja'))
        self.fields['language'].choices = BLANK_CHOICE_DASH + self.fields['language'].choices
        self.fields['os'].choices = BLANK_CHOICE_DASH + self.fields['os'].choices
        self.fields['verified'].choices = BLANK_CHOICE_DASH + [(3, _('Only'))] + self.fields['verified'].choices
        del(self.fields['verified'].choices[-1])
        self.fields['verified'].initial = None
        self.fields['os'].initial = None
        self.fields['language'].initial = None
        del(self.fields['status'].choices[0])
        del(self.fields['status'].choices[0])
        self.fields['status'].choices = BLANK_CHOICE_DASH + [('only', _('Only'))] + self.fields['status'].choices
        #self.fields['status'].choices.insert(1, ('only', _('Only'))) this doesn't work i don't know why

    class Meta:
        model = models.Account
        fields = ('search', 'attribute', 'best_girl', 'private', 'status', 'language', 'id_search', 'os', 'verified', 'center_attribute', 'center_rarity', 'with_friend_id', 'accept_friend_requests', 'play_with', 'ordering', 'reverse_order')

class TeamForm(ModelForm):
    """
    Account is required to initialize this form.
    Account must contain prefetched deck.
    Team instance must contain prefetched all_members
    """
    card0 = forms.TypedChoiceField(coerce=int, empty_value=None, choices=[], required=False)
    card1 = forms.TypedChoiceField(coerce=int, empty_value=None, choices=[], required=False)
    card2 = forms.TypedChoiceField(coerce=int, empty_value=None, choices=[], required=False)
    card3 = forms.TypedChoiceField(coerce=int, empty_value=None, choices=[], required=False)
    card4 = forms.TypedChoiceField(coerce=int, empty_value=None, choices=[], required=False)
    card5 = forms.TypedChoiceField(coerce=int, empty_value=None, choices=[], required=False)
    card6 = forms.TypedChoiceField(coerce=int, empty_value=None, choices=[], required=False)
    card7 = forms.TypedChoiceField(coerce=int, empty_value=None, choices=[], required=False)
    card8 = forms.TypedChoiceField(coerce=int, empty_value=None, choices=[], required=False)

    def __init__(self, *args, **kwargs):
        account = kwargs.pop('account', None)
        super(TeamForm, self).__init__(*args, **kwargs)
        deck_choices = [(ownedcard.id, _ownedcard_label(ownedcard)) for ownedcard in account.deck]
        for i in range(9):
            self.fields['card' + str(i)].choices = BLANK_CHOICE_DASH + deck_choices
        if self.instance and hasattr(self.instance, 'all_members'):
            for member in getattr(self.instance, 'all_members'):
                self.fields['card' + str(member.position)].initial = member.ownedcard.id

    def clean(self):
        for i in range(9):
            ownedcard_id = self.cleaned_data['card' + str(i)]
            if ownedcard_id is not None:
                for j in range(9):
                    if i != j and ownedcard_id == self.cleaned_data['card' + str(j)]:
                        raise forms.ValidationError(_("The same card can\'t appear twice in the same team."))
        return self.cleaned_data

    class Meta:
        model = models.Team
        fields = ('name', 'card0', 'card1', 'card2', 'card3', 'card4', 'card5', 'card6', 'card7', 'card8')

class PrivateMessageForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(PrivateMessageForm, self).__init__(*args, **kwargs)
        self.fields['message'].label = _('New Message')

    class Meta:
        model = models.PrivateMessage
        fields = ('message',)

skill_choices = [(name, name) for (name, icon) in skillsIcons.items()] + [('Special', 'Special')]
attributes = [name for (name, localized) in models.ATTRIBUTE_CHOICES if name != 'All']
effects = [unicode(name) for name in models.CENTER_SKILL_TRANSLATE]
center_skill_choices = []
for attribute in attributes:
    for effect in effects:
        center_skill_choices.append((attribute + ' ' +  effect))
center_skill_choices = [(skill, skill) for skill in center_skill_choices]

class StaffCard(ModelForm):
    skill = ChoiceField(label=_('Skill'), choices=BLANK_CHOICE_DASH + skill_choices, required=False)
    center_skill = ChoiceField(label=_('Center Skill'), choices=BLANK_CHOICE_DASH + center_skill_choices, required=False)

    def __init__(self, *args, **kwargs):
        super(StaffCard, self).__init__(*args, **kwargs)
        self.fields['japanese_skill'].help_text = _(u'Name of the skill in Japanese. Also corresponds to the name of the card. Example: "和太鼓名人"')
        self.fields['skill_details'].help_text = _(u'Use the formatted string details available here: https://goo.gl/CsYVa3 and replace "N" with the corresponding value.')
        self.fields['video_story'].help_text = _(u'Link to a YouTube video. Make sure it uses the following format: http://www.youtube.com/watch?v=Mcz9C67Pd1c')
        self.fields['japanese_video_story'].help_text = _(u'Link to a YouTube video. Make sure it uses the following format: http://www.youtube.com/watch?v=Mcz9C67Pd1c')
        for field in ['minimum_statistics_smile', 'minimum_statistics_pure', 'minimum_statistics_cool', 'non_idolized_maximum_statistics_smile', 'non_idolized_maximum_statistics_pure', 'non_idolized_maximum_statistics_cool', 'idolized_maximum_statistics_smile', 'idolized_maximum_statistics_pure', 'idolized_maximum_statistics_cool']:
            self.fields[field].required=False

    def save(self, commit=True):
        instance = super(StaffCard, self).save(commit=False)
        for field in ['minimum_statistics_smile', 'minimum_statistics_pure', 'minimum_statistics_cool', 'non_idolized_maximum_statistics_smile', 'non_idolized_maximum_statistics_pure', 'non_idolized_maximum_statistics_cool', 'idolized_maximum_statistics_smile', 'idolized_maximum_statistics_pure', 'idolized_maximum_statistics_cool']:
            if not getattr(instance, field):
                setattr(instance, field, 0)
        if instance.rarity == 'N' or instance.is_promo:
            for field in ['non_idolized_maximum_statistics_smile', 'non_idolized_maximum_statistics_pure', 'non_idolized_maximum_statistics_cool']:
                setattr(instance, field, 0)
        for field in ['japanese_collection', 'english_collection', 'translated_collection', 'promo_item', 'promo_link', 'japanese_skill', 'skill_details', 'japanese_skill_details', 'video_story', 'japanese_video_story']:
            if not getattr(instance, field):
                setattr(instance, field, None)
        if commit:
            instance.save()
        return instance

    class Meta:
        model = models.Card
        fields = ('id', 'game_id', 'idol', 'japanese_collection', 'english_collection', 'translated_collection', 'rarity', 'attribute', 'is_promo', 'promo_item', 'promo_link', 'release_date', 'event', 'other_event', 'is_special', 'japan_only', 'seal_shop', 'hp', 'minimum_statistics_smile', 'minimum_statistics_pure', 'minimum_statistics_cool', 'non_idolized_maximum_statistics_smile', 'non_idolized_maximum_statistics_pure', 'non_idolized_maximum_statistics_cool', 'idolized_maximum_statistics_smile', 'idolized_maximum_statistics_pure', 'idolized_maximum_statistics_cool', 'skill', 'japanese_skill', 'skill_details', 'japanese_skill_details', 'center_skill', 'transparent_image', 'transparent_idolized_image', 'card_image', 'card_idolized_image', 'english_card_image', 'english_card_idolized_image', 'round_card_image', 'round_card_idolized_image', 'english_round_card_image', 'english_round_card_idolized_image', 'clean_ur', 'clean_ur_idolized', 'video_story', 'japanese_video_story', 'ur_pair', 'ur_pair_reverse', 'ur_pair_idolized_reverse')

class StaffEvent(ModelForm):
    def __init__(self, *args, **kwargs):
        super(StaffEvent, self).__init__(*args, **kwargs)
#        for field in ['beginning', 'end']:
#            self.fields[field].required=True

    def save(self, commit=True):
        instance = super(StaffEvent, self).save(commit=False)
        for field in ['romaji_name', 'english_name']:
            if not getattr(instance, field):
                setattr(instance, field, None)

    class Meta:
        model = models.Event
        fields = ('japanese_name', 'romaji_name', 'beginning', 'end', 'japanese_t1_points', 'japanese_t2_points', 'japanese_t1_rank', 'japanese_t2_rank', 'image', 'english_name', 'english_beginning', 'english_end', 'english_t1_points', 'english_t2_points', 'english_t1_rank', 'english_t2_rank', 'english_image', 'note')


class StaffSong(ModelForm):
    main_unit = ChoiceField(label=_('Main Unit'), choices=BLANK_CHOICE_DASH + [
        ('μ\'s', 'μ\'s'),
        ('Aqours', 'Aqours'),
    ], required=False)
    daily_rotation = ChoiceField(label=_('Daily Rotation'), choices=BLANK_CHOICE_DASH + [('A', 'A'), ('B', 'B'), ('C', 'C',)], required=False)
    daily_rotation_position = ChoiceField(label=_('Daily Rotation Position'), choices=BLANK_CHOICE_DASH + [(i, i) for i in range(1, 11)], required=False)
    def __init__(self, *args, **kwargs):
        super(StaffSong, self).__init__(*args, **kwargs)
        self.fields['itunes_id'].help_text = _(u'Leave this empty if you don\'t know what this is!')

    def save(self, commit=True):
        instance = super(StaffSong, self).save(commit=False)
        for field in ['romaji_name', 'translated_name']:
            if not getattr(instance, field):
                setattr(instance, field, None)

    class Meta:
        model = models.Song
        fields = ('name', 'romaji_name', 'translated_name', 'attribute', 'BPM', 'time', 'main_unit', 'event', 'rank', 'daily_rotation', 'daily_rotation_position', 'image', 'easy_difficulty', 'easy_notes', 'normal_difficulty', 'normal_notes', 'hard_difficulty', 'hard_notes', 'expert_difficulty', 'expert_random_difficulty', 'expert_notes', 'master_difficulty', 'master_notes', 'available', 'itunes_id')
