from zope.event import notify
from zope.interface import implements
from zope.site.hooks import setSite

from Products.GenericSetup.tool import SetupTool

from Products.CMFPlone.events import SiteManagerCreatedEvent
from Products.CMFPlone.interfaces import INonInstallable
from Products.CMFPlone.Portal import PloneSite

_TOOL_ID = 'portal_setup'
_DEFAULT_PROFILE = 'Products.CMFPlone:plone'
_CONTENT_PROFILE = 'Products.CMFPlone:plone-content'

# A little hint for PloneTestCase
_IMREALLYPLONE4 = True

class HiddenProfiles(object):
    implements(INonInstallable)

    def getNonInstallableProfiles(self):
        return [_DEFAULT_PROFILE,
                _CONTENT_PROFILE,
                u'Products.Archetypes:Archetypes',
                u'Products.CMFDiffTool:CMFDiffTool',
                u'Products.CMFEditions:CMFEditions',
                u'Products.CMFFormController:CMFFormController',
                u'Products.CMFPlone:dependencies',
                u'Products.CMFPlone:testfixture',
                u'Products.CMFQuickInstallerTool:CMFQuickInstallerTool',
                u'Products.NuPlone:uninstall',
                u'Products.MimetypesRegistry:MimetypesRegistry',
                u'Products.PasswordResetTool:PasswordResetTool',
                u'Products.PortalTransforms:PortalTransforms',
                u'Products.PloneLanguageTool:PloneLanguageTool',
                u'Products.PlonePAS:PlonePAS',
                u'archetypes.referencebrowserwidget:default',
                u'borg.localrole:default',
                u'Products.TinyMCE:TinyMCE',
                u'Products.TinyMCE:upgrade_10_to_11',
                u'Products.TinyMCE:uninstall',
                u'plone.browserlayer:default',
                u'plone.keyring:default',
                u'plone.portlet.static:default',
                u'plone.portlet.collection:default',
                u'plone.protect:default',
                u'plonetheme.sunburst:uninstall',
                u'plone.app.blob:default',
                u'plone.app.blob:file-replacement',
                u'plone.app.blob:image-replacement',
                u'plone.app.blob:sample-type',
                u'plone.app.imaging:default',
                ]


def addPloneSite(context, site_id, title='', description='',
                 create_userfolder=True, email_from_address='',
                 email_from_name='', validate_email=False,
                 profile_id=_DEFAULT_PROFILE, snapshot=False,
                 extension_ids=(), setup_content=True, default_language='en'):
    """ Add a PloneSite to 'dispatcher', configured according to 'profile_id'.
    """
    context._setObject(site_id, PloneSite(site_id))
    site = context._getOb(site_id)
    site.setLanguage(default_language)

    site[_TOOL_ID] = SetupTool(_TOOL_ID)
    setup_tool = site[_TOOL_ID]

    notify(SiteManagerCreatedEvent(site))
    setSite(site)

    setup_tool.setBaselineContext('profile-%s' % profile_id)
    setup_tool.runAllImportStepsFromProfile('profile-%s' % profile_id)
    if setup_content:
        setup_tool.runAllImportStepsFromProfile('profile-%s' % _CONTENT_PROFILE)
    for extension_id in extension_ids:
        setup_tool.runAllImportStepsFromProfile('profile-%s' % extension_id)

    # Try to make the title work with Unicode
    if isinstance(title, str):
        title = unicode(title, 'utf-8', 'ignore')

    props = {}
    prop_keys = ['title', 'description', 'email_from_address',
                 'email_from_name', 'validate_email']
    loc_dict = locals()
    for key in prop_keys:
        if loc_dict[key]:
            props[key] = loc_dict[key]
    if props:
        site.manage_changeProperties(**props)

    if snapshot is True:
        setup_tool.createSnapshot('initial_configuration')

    return site
