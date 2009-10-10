"""
CMFPlone setup handlers.
"""

from borg.localrole.utils import replace_local_role_manager
from five.localsitemanager import make_objectmanager_site
from plone.i18n.normalizer.interfaces import IURLNormalizer
from plone.portlets.interfaces import ILocalPortletAssignmentManager
from plone.portlets.interfaces import IPortletManager

from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.event import notify
from zope.i18n.interfaces import ITranslationDomain
from zope.i18n.interfaces import IUserPreferredLanguages
from zope.i18n.locales import locales, LoadLocaleError
from zope.interface import implements
from zope.location.interfaces import ISite
from zope.site.hooks import setSite

from Acquisition import aq_base, aq_get
from Products.CMFCore.utils import getToolByName
from Products.ATContentTypes.lib import constraintypes
from Products.CMFDefault.utils import bodyfinder
from Products.CMFQuickInstallerTool.interfaces import INonInstallable
from Products.StandardCacheManagers.AcceleratedHTTPCacheManager import \
     AcceleratedHTTPCacheManager
from Products.StandardCacheManagers.RAMCacheManager import RAMCacheManager

from Products.CMFPlone.utils import _createObjectByType
from Products.CMFPlone.events import SiteManagerCreatedEvent
from Products.CMFPlone.factory import _DEFAULT_PROFILE
from Products.CMFPlone.interfaces import IMigrationTool
from Products.CMFPlone.Portal import member_indexhtml


class HiddenProducts(object):
    implements(INonInstallable)

    def getNonInstallableProducts(self):
        return [
            'Archetypes', 'Products.Archetypes',
            'ATContentTypes', 'Products.ATContentTypes',
            'ATReferenceBrowserWidget', 'Products.ATReferenceBrowserWidget',
            'archetypes.referencebrowserwidget',
            'CMFActionIcons', 'Products.CMFActionIcons',
            'CMFCalendar', 'Products.CMFCalendar',
            'CMFDefault', 'Products.CMFDefault',
            'CMFPlone', 'Products.CMFPlone', 'Products.CMFPlone.migrations',
            'CMFTopic', 'Products.CMFTopic',
            'CMFUid', 'Products.CMFUid',
            'DCWorkflow', 'Products.DCWorkflow',
            'PasswordResetTool', 'Products.PasswordResetTool',
            'PlonePAS', 'Products.PlonePAS',
            'wicked.at',
            'kupu', 'Products.kupu',
            'PloneLanguageTool', 'Products.PloneLanguageTool',
            'Kupu', 'Products.Kupu',
            'CMFFormController', 'Products.CMFFormController',
            'MimetypesRegistry', 'Products.MimetypesRegistry',
            'PortalTransforms', 'Products.PortalTransforms',
            'CMFDiffTool', 'Products.CMFDiffTool',
            'CMFEditions', 'Products.CMFEditions',
            'Products.NuPlone',
            'plone.portlet.static',
            'plone.portlet.collection',
            'borg.localrole',
            'plone.keyring',
            'plone.protect',
            ]


class PloneGenerator:

    def installDependencies(self, p):
        st=getToolByName(p, "portal_setup")
        st.runAllImportStepsFromProfile("profile-Products.CMFPlone:dependencies")

    def addCacheHandlers(self, p):
        """ Add RAM and AcceleratedHTTP cache handlers """
        mgrs = [(AcceleratedHTTPCacheManager, 'HTTPCache'),
                (RAMCacheManager, 'RAMCache'),
                (RAMCacheManager, 'ResourceRegistryCache'),
                ]
        for mgr_class, mgr_id in mgrs:
            existing = p._getOb(mgr_id, None)
            if existing is None:
                p._setObject(mgr_id, mgr_class(mgr_id))
            else:
                unwrapped = aq_base(existing)
                if not isinstance(unwrapped, mgr_class):
                    p._delObject(mgr_id)
                    p._setObject(mgr_id, mgr_class(mgr_id))

    def addCacheForResourceRegistry(self, portal):
        ram_cache_id = 'ResourceRegistryCache'
        if ram_cache_id in portal:
            cache = getattr(portal, ram_cache_id)
            settings = cache.getSettings()
            settings['max_age'] = 24*3600 # keep for up to 24 hours
            settings['request_vars'] = ('URL',)
            cache.manage_editProps('Cache for saved ResourceRegistry files', settings)
        reg = getToolByName(portal, 'portal_css', None)
        if reg is not None and getattr(aq_base(reg), 'ZCacheable_setManagerId', None) is not None:
            reg.ZCacheable_setManagerId(ram_cache_id)
            reg.ZCacheable_setEnabled(1)

        reg = getToolByName(portal, 'portal_kss', None)
        if reg is not None and getattr(aq_base(reg), 'ZCacheable_setManagerId', None) is not None:
            reg.ZCacheable_setManagerId(ram_cache_id)
            reg.ZCacheable_setEnabled(1)

        reg = getToolByName(portal, 'portal_javascripts', None)
        if reg is not None and getattr(aq_base(reg), 'ZCacheable_setManagerId', None) is not None:
            reg.ZCacheable_setManagerId(ram_cache_id)
            reg.ZCacheable_setEnabled(1)

    def setupPortalContent(self, p):
        """
        Import default plone content
        """
        existing = p.keys()

        wftool = getToolByName(p, "portal_workflow")

        # Figure out the current user preferred language
        language = None
        locale = None
        target_language = None
        request = getattr(p, 'REQUEST', None)
        if request is not None:
            pl = IUserPreferredLanguages(request)
            if pl is not None:
                languages = pl.getPreferredLanguages()
                for httplang in languages:
                    parts = (httplang.split('-') + [None, None])[:3]
                    try:
                        locale = locales.getLocale(*parts)
                        break
                    except LoadLocaleError:
                        # Just try the next combination
                        pass
                if len(languages) > 0:
                    language = languages[0]

        # Language to be used to translate the content
        target_language = language

        # Set the default language of the portal
        if language is not None and locale is not None:
            localeid = locale.getLocaleID()
            base_language = locale.id.language
            target_language = localeid

            # If we get a territory, we enable the combined language codes
            use_combined = False
            if locale.id.territory:
                use_combined = True

            # As we have a sensible language code set now, we disable the
            # start neutral functionality
            tool = getToolByName(p, "portal_languages")
            pprop = getToolByName(p, "portal_properties")
            sheet = pprop.site_properties

            tool.manage_setLanguageSettings(language,
                [language],
                setUseCombinedLanguageCodes=use_combined,
                startNeutral=False)

            # Set the first day of the week, defaulting to Sunday, as the
            # locale data doesn't provide a value for English. European
            # languages / countries have an entry of Monday, though.
            calendar = getToolByName(p, "portal_calendar", None)
            if calendar is not None:
                first = 6
                gregorian = locale.dates.calendars.get(u'gregorian', None)
                if gregorian is not None:
                    first = gregorian.week.get('firstDay', None)
                    # on the locale object we have: mon : 1 ... sun : 7
                    # on the calendar tool we have: mon : 0 ... sun : 6
                    if first is not None:
                        first = first - 1

                calendar.firstweekday = first

            # Enable visible_ids for non-latin scripts

            # See if we have an url normalizer
            normalizer = queryUtility(IURLNormalizer, name=localeid)
            if normalizer is None:
                normalizer = queryUtility(IURLNormalizer, name=base_language)

            # If we get a script other than Latn we enable visible_ids
            if locale.id.script is not None:
                if locale.id.script.lower() != 'latn':
                    sheet.visible_ids = True

            # If we have a normalizer it is safe to disable the visible ids
            if normalizer is not None:
                sheet.visible_ids = False

        # The front-page
        if 'front-page' not in existing:
            front_title = u'Welcome to Plone'
            front_desc = u'Congratulations! You have successfully installed Plone.'
            front_text = None
            _createObjectByType('Document', p, id='front-page',
                                title=front_title, description=front_desc)
            fp = p['front-page']
            if wftool.getInfoFor(fp, 'review_state') != 'published':
                wftool.doActionFor(fp, 'publish')

            if target_language is not None:
                util = queryUtility(ITranslationDomain, 'plonefrontpage')
                if util is not None:
                    front_title = util.translate(u'front-title',
                                       target_language=target_language,
                                       default="Welcome to Plone")
                    front_desc = util.translate(u'front-description',
                                       target_language=target_language,
                                       default="Congratulations! You have successfully installed Plone.")
                    translated_text = util.translate(u'front-text',
                                       target_language=target_language)
                    fp.setLanguage(language)
                    if translated_text != u'front-text':
                        front_text = translated_text

            if front_text is None and request is not None:
                view = queryMultiAdapter((p, request),
                    name='plone_frontpage_setup')
                if view is not None:
                    front_text = bodyfinder(view.index()).strip()

            fp.setTitle(front_title)
            fp.setDescription(front_desc)
            fp.setText(front_text, mimetype='text/html')

            # Show off presentation mode
            fp.setPresentation(True)

            # Mark as fully created
            fp.unmarkCreationFlag()

            p.setDefaultPage('front-page')
            fp.reindexObject()

        # News topic
        if 'news' not in existing:
            news_title = 'News'
            news_desc = 'Site News'
            if target_language is not None:
                util = queryUtility(ITranslationDomain, 'plonefrontpage')
                if util is not None:
                    news_title = util.translate(u'news-title',
                                           target_language=target_language,
                                           default='News')
                    news_desc = util.translate(u'news-description',
                                          target_language=target_language,
                                          default='Site News')

            _createObjectByType('Large Plone Folder', p, id='news',
                                title=news_title, description=news_desc)
            _createObjectByType('Topic', p.news, id='aggregator',
                                title=news_title, description=news_desc)

            folder = p.news
            folder.setConstrainTypesMode(constraintypes.ENABLED)
            folder.setLocallyAllowedTypes(['News Item'])
            folder.setImmediatelyAddableTypes(['News Item'])
            folder.setDefaultPage('aggregator')
            folder.unmarkCreationFlag()
            if language is not None:
                folder.setLanguage(language)

            if wftool.getInfoFor(folder, 'review_state') != 'published':
                wftool.doActionFor(folder, 'publish')

            topic = p.news.aggregator
            if language is not None:
                topic.setLanguage(language)
            type_crit = topic.addCriterion('Type','ATPortalTypeCriterion')
            type_crit.setValue('News Item')
            sort_crit = topic.addCriterion('created','ATSortCriterion')
            state_crit = topic.addCriterion('review_state', 'ATSimpleStringCriterion')
            state_crit.setValue('published')
            topic.setSortCriterion('effective', True)
            topic.setLayout('folder_summary_view')
            topic.unmarkCreationFlag()

            if wftool.getInfoFor(topic, 'review_state') != 'published':
                wftool.doActionFor(topic, 'publish')

        # Events topic
        if 'events' not in existing:
            events_title = 'Events'
            events_desc = 'Site Events'
            if target_language is not None:
                util = queryUtility(ITranslationDomain, 'plonefrontpage')
                if util is not None:
                    events_title = util.translate(u'events-title',
                                           target_language=target_language,
                                           default='Events')
                    events_desc = util.translate(u'events-description',
                                          target_language=target_language,
                                          default='Site Events')

            _createObjectByType('Large Plone Folder', p, id='events',
                                title=events_title, description=events_desc)
            _createObjectByType('Topic', p.events, id='aggregator',
                                title=events_title, description=events_desc)
            folder = p.events
            folder.setConstrainTypesMode(constraintypes.ENABLED)
            folder.setLocallyAllowedTypes(['Event'])
            folder.setImmediatelyAddableTypes(['Event'])
            folder.setDefaultPage('aggregator')
            folder.unmarkCreationFlag()
            if language is not None:
                folder.setLanguage(language)

            if wftool.getInfoFor(folder, 'review_state') != 'published':
                wftool.doActionFor(folder, 'publish')

            topic = folder.aggregator
            topic.unmarkCreationFlag()
            if language is not None:
                topic.setLanguage(language)
            type_crit = topic.addCriterion('Type','ATPortalTypeCriterion')
            type_crit.setValue('Event')
            sort_crit = topic.addCriterion('start','ATSortCriterion')
            state_crit = topic.addCriterion('review_state', 'ATSimpleStringCriterion')
            state_crit.setValue('published')
            date_crit = topic.addCriterion('start', 'ATFriendlyDateCriteria')
            # Set date reference to now
            date_crit.setValue(0)
            # Only take events in the future
            date_crit.setDateRange('+') # This is irrelevant when the date is now
            date_crit.setOperation('more')
        else:
            topic = p.events

        if wftool.getInfoFor(topic, 'review_state') != 'published':
            wftool.doActionFor(topic, 'publish')

        # Previous events subtopic
        if 'previous' not in topic.objectIds():
            prev_events_title = 'Past Events'
            prev_events_desc = 'Events which have already happened.'
            if target_language is not None:
                util = queryUtility(ITranslationDomain, 'plonefrontpage')
                if util is not None:
                    prev_events_title = util.translate(u'prev-events-title',
                                           target_language=target_language,
                                           default='Past Events')
                    prev_events_desc = util.translate(u'prev-events-description',
                                          target_language=target_language,
                                          default='Events which have already happened.')

            _createObjectByType('Topic', topic, id='previous',
                                title=prev_events_title,
                                description=prev_events_desc)
            topic = topic.previous
            if language is not None:
                topic.setLanguage(language)
            topic.setAcquireCriteria(True)
            topic.unmarkCreationFlag()
            sort_crit = topic.addCriterion('end','ATSortCriterion')
            sort_crit.setReversed(True)
            date_crit = topic.addCriterion('end','ATFriendlyDateCriteria')
            # Set date reference to now
            date_crit.setValue(0)
            # Only take events in the past
            date_crit.setDateRange('-') # This is irrelevant when the date is now
            date_crit.setOperation('less')

            if wftool.getInfoFor(topic, 'review_state') != 'published':
                wftool.doActionFor(topic, 'publish')

        # configure Members folder
        members_title = 'Users'
        members_desc = "Container for users' home directories"
        if 'Members' not in existing:
            _createObjectByType('Large Plone Folder', p, id='Members',
                                title=members_title, description=members_desc)

        if 'Members' in p.keys():
            if target_language is not None:
                util = queryUtility(ITranslationDomain, 'plonefrontpage')
                if util is not None:
                    members_title = util.translate(u'members-title',
                                           target_language=target_language,
                                           default='Users')
                    members_desc = util.translate(u'members-description',
                                          target_language=target_language,
                                          default="Container for users' home directories")

            members = getattr(p , 'Members')
            members.setTitle(members_title)
            members.setDescription(members_desc)
            members.unmarkCreationFlag()
            if language is not None:
                members.setLanguage(language)
            members.reindexObject()

            if wftool.getInfoFor(members, 'review_state') != 'published':
                wftool.doActionFor(members, 'publish')

            # add index_html to Members area
            if 'index_html' not in members.objectIds():
                addPy = members.manage_addProduct['PythonScripts'].manage_addPythonScript
                addPy('index_html')
                index_html = getattr(members, 'index_html')
                index_html.write(member_indexhtml)
                index_html.ZPythonScript_setTitle('User Search')

            # Block all right column portlets by default
            manager = queryUtility(IPortletManager, name='plone.rightcolumn')
            if manager is not None:
                assignable = queryMultiAdapter((members, manager), ILocalPortletAssignmentManager)
                assignable.setBlacklistStatus('context', True)
                assignable.setBlacklistStatus('group', True)
                assignable.setBlacklistStatus('content_type', True)


    def setProfileVersion(self, portal):
        """
        Set profile version.
        """
        mt = queryUtility(IMigrationTool)
        mt.setInstanceVersion(mt.getFileSystemVersion())
        setup = getToolByName(portal, 'portal_setup')
        version = setup.getVersionForProfile(_DEFAULT_PROFILE)
        setup.setLastVersionForProfile(_DEFAULT_PROFILE, version)

    def enableSyndication(self, portal, out):
        syn = getToolByName(portal, 'portal_syndication', None)
        if syn is not None:
            syn.editProperties(isAllowed=True)
            cat = getToolByName(portal, 'portal_catalog', None)
            if cat is not None:
                topics = cat(portal_type='Topic')
                for b in topics:
                    topic = b.getObject()
                    # If syndication is already enabled then another nasty string
                    # exception gets raised in CMFDefault
                    if topic is not None and not syn.isSyndicationAllowed(topic):
                        syn.enableSyndication(topic)
                        out.append('Enabled syndication on %s'%b.getPath())

    def enableSite(self, portal):
        """
        Make the portal a Zope3 site and create a site manager.
        """
        if not ISite.providedBy(portal):
            make_objectmanager_site(portal)
        # The following event is primarily useful for setting the site hooks
        # during test runs.
        notify(SiteManagerCreatedEvent(portal))

    def assignTitles(self, portal, out):
        titles={
         'acl_users':'User / Group storage and authentication settings',
         'archetype_tool':'Archetypes specific settings',
         'caching_policy_manager':'Settings related to proxy caching',
         'content_type_registry':'MIME type settings',
         'error_log':'Error and exceptions log viewer',
         'kupu_library_tool':'Kupu Visual Editor settings',
         'MailHost':'Mail server settings for outgoing mail',
         'mimetypes_registry':'MIME types recognized by Plone',
         'plone_utils':'Various utility methods',
         'portal_actionicons':'Associates actions with icons',
         'portal_actions':'Contains custom tabs and buttons',
         'portal_atct':'Collection and image scales settings',
         'portal_calendar':'Controls how events are shown',
         'portal_catalog':'Indexes all content in the site',
         'portal_controlpanel':'Registry of control panel screen',
         'portal_css':'Registry of CSS files',
         'portal_diff':'Settings for content version comparisions',
         'portal_discussion':'Controls how discussions are stored',
         'portal_factory':'Responsible for the creation of content objects',
         'portal_form_controller':'Registration of form and validation chains',
         'portal_groupdata':'Handles properties on groups',
         'portal_groups':'Handles group related functionality',
         'portal_interface':'Allows to query object interfaces',
         'portal_javascripts':'Registry of JavaScript files',
         'portal_kss':'Registry of Kinetic Style Sheets',
         'portal_languages':'Language specific settings',
         'portal_membership':'Handles membership policies',
         'portal_memberdata':'Handles the available properties on members',
         'portal_metadata':'Controls metadata like keywords, copyrights, etc',
         'portal_migration':'Upgrades to newer Plone versions',
         'portal_password_reset':'Handles password retention policy',
         'portal_properties':'General settings registry',
         'portal_quickinstaller':'Allows to install/uninstall products',
         'portal_registration':'Handles registration of new users',
         'portal_setup':'Add-on and configuration management',
         'portal_skins':'Controls skin behaviour (search order etc)',
         'portal_syndication':'Generates RSS for folders',
         'portal_transforms': 'Handles data conversion between MIME types',
         'portal_types':'Controls the available content types in your portal',
         'portal_undo':'Defines actions and functionality related to undo',
         'portal_url':'Methods to anchor you to the root of your Plone site',
         'portal_view_customizations':'Template customizations',
         'portal_workflow':'Contains workflow definitions for your portal',
         'reference_catalog':'Catalog of content references',
         'translation_service':'Provides access to the translation machinery',
         'uid_catalog':'Catalog of unique content identifiers',
         }

        for oid in portal.objectIds():
            title=titles.get(oid, None)
            if title:
                setattr(aq_get(portal, oid), 'title', title)
        out.append('Assigned titles to portal tools.')

def importSite(context):
    """
    Import site settings.
    """
    site = context.getSite()
    gen = PloneGenerator()
    gen.enableSite(site)
    setSite(site)

def importFinalSteps(context):
    """
    Final Plone import steps.
    """
    # Only run step if a flag file is present (e.g. not an extension profile)
    if context.readDataFile('plone-final.txt') is None:
        return
    out = []
    site = context.getSite()
    pprop = getToolByName(site, 'portal_properties')
    pmembership = getToolByName(site, 'portal_membership')
    gen = PloneGenerator()
    gen.setProfileVersion(site)
    gen.enableSyndication(site, out)
    pmembership.memberareaCreationFlag = False
    gen.installDependencies(site)
    gen.assignTitles(site, out)
    replace_local_role_manager(site)
    gen.addCacheHandlers(site)
    gen.addCacheForResourceRegistry(site)

def importContent(context):
    """
    Final Plone content import step.
    """
    # Only run step if a flag file is present
    if context.readDataFile('plone-content.txt') is None:
        return
    site = context.getSite()
    gen = PloneGenerator()
    gen.setupPortalContent(site)

def updateWorkflowRoleMappings(context):
    """
    If an extension profile (such as the testfixture one) switches default,
    workflows, this import handler will make sure object security works
    properly.
    """
    # Only run step if a flag file is present
    if context.readDataFile('plone-update-workflow-rolemap.txt') is None:
        return
    site = context.getSite()
    portal_workflow = getToolByName(site, 'portal_workflow')
    portal_workflow.updateRoleMappings()
