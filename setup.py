from setuptools import setup, find_packages
import os.path

version = '3.2rc1'

setup(name='Plone',
      version=version,
      description="The Plone Content Management System",
      long_description=open("README.txt").read() +  "\n" +
                       open(os.path.join("docs", "NEWS.txt")).read(),
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Environment :: Web Environment",
          "Framework :: Plone",
          "Framework :: Zope2",
          "License :: OSI Approved :: GNU General Public License (GPL)",
          "Operating System :: OS Independent",
          "Programming Language :: Python",
          "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
          "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='Plone CMF python Zope',
      author='Plone Foundation',
      author_email='plone-developers@lists.sourceforge.net',
      url='http://plone.org/',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['Products'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'elementtree',
          'Products.kupu',
          'Products.AdvancedQuery',
          'Products.Archetypes',
          'Products.ATReferenceBrowserWidget',
          'Products.ATContentTypes',
          'Products.CMFActionIcons',
          'Products.CMFCalendar',
          'Products.CMFCore',
          'Products.CMFDefault',
          'Products.CMFDiffTool',
          'Products.CMFDynamicViewFTI',
          'Products.CMFEditions',
          'Products.CMFFormController',
          'Products.CMFPlacefulWorkflow',
          'Products.CMFQuickInstallerTool',
          'Products.CMFTopic',
          'Products.CMFUid',
          'Products.DCWorkflow',
          'Products.ExtendedPathIndex',
          'Products.ExternalEditor',
          'Products.GenericSetup >=1.4',
          'Products.GroupUserFolder',
          'Products.MimetypesRegistry',
          'Products.PasswordResetTool',
          'Products.PlacelessTranslationService',
          'Products.PloneLanguageTool',
          'Products.PlonePAS',
          'Products.PluggableAuthService',
          'Products.PluginRegistry',
          'Products.PortalTransforms',
          'Products.ResourceRegistries',
          'Products.SecureMailHost',
          'Products.statusmessages',
          'archetypes.kss',
          'borg.localrole',
          'kss.core',
          'plone.app.contentmenu >= 1.1.6dev-r22380',
          'plone.app.content',
          'plone.app.contentrules',
          'plone.app.controlpanel',
          'plone.app.customerize',
          'plone.app.form',
          'plone.app.i18n',
          'plone.app.iterate',
          'plone.app.kss',
          'plone.app.layout >=1.1.7dev-r23744',
          'plone.app.linkintegrity >=1.0.3',
          'plone.app.locales',
          'plone.app.openid',
          'plone.app.portlets',
          'plone.app.redirector',
          'plone.app.viewletmanager',
          'plone.app.vocabularies',
          'plone.app.workflow',
          'plone.browserlayer >= 1.0rc4',
          'plone.contentrules',
          'plone.fieldsets',
          'plone.i18n',
          'plone.intelligenttext',
          'plone.locking',
          'plone.memoize',
          'plone.openid',
          'plone.portlets',
          'plone.protect > 1.0',
          'plone.session',
          'plone.theme',
          'plone.portlet.collection',
          'plone.portlet.static',
          'wicked',
          'five.customerize',
          'five.localsitemanager',
# Needed for testing only
          'Products.PloneTestCase',
      ],
      )
