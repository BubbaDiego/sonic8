# Sonic UI Components — Catalog (auto-generated)

> Source of truth: `docs/spec/ui.manifest.yaml`  
> Generated: 2025-11-22 11:23:24

Use this catalog to discover components, props, and example usage.  
To regenerate: `python backend/scripts/build_ui_components_doc.py`

## Table of contents
- [Accordion](#accordion)
- [ActionBar](#actionbar)
- [ActionsCell](#actionscell)
- [ActiveTickets](#activetickets)
- [AddColumn](#addcolumn)
- [AddItem](#additem)
- [AddItemComment](#additemcomment)
- [AddMenuItem](#addmenuitem)
- [AddressCell](#addresscell)
- [AddressForm](#addressform)
- [AddStory](#addstory)
- [AddStoryComment](#addstorycomment)
- [AddThresholdDialog](#addthresholddialog)
- [AlertColumnDelete](#alertcolumndelete)
- [AlertItemDelete](#alertitemdelete)
- [AlertStoryDelete](#alertstorydelete)
- [AlertThresholdsPage](#alertthresholdspage)
- [Analytics](#analytics)
- [AnalyticsChartCard](#analyticschartcard)
- [AnimateButton](#animatebutton)
- [Animation](#animation)
- [ApexAreaChart](#apexareachart)
- [ApexBarChart](#apexbarchart)
- [Apexchart](#apexchart)
- [ApexColumnChart](#apexcolumnchart)
- [ApexLineChart](#apexlinechart)
- [ApexMixedChart](#apexmixedchart)
- [ApexPieChart](#apexpiechart)
- [ApexPolarChart](#apexpolarchart)
- [ApexRedialBarChart](#apexredialbarchart)
- [App](#app)
- [AppBar](#appbar)
- [AppGrid](#appgrid)
- [ApplicationSales](#applicationsales)
- [AskConfirmationBeforeSave](#askconfirmationbeforesave)
- [AssetLogo](#assetlogo)
- [AttachmentCard](#attachmentcard)
- [Auth0ContextProvider](#auth0contextprovider)
- [Auth0Login](#auth0login)
- [Auth0Provider](#auth0provider)
- [Auth0Register](#auth0register)
- [AuthCardWrapper](#authcardwrapper)
- [AuthCheckMail](#authcheckmail)
- [AuthCodeVerification](#authcodeverification)
- [AuthFooter](#authfooter)
- [AuthForgotPassword](#authforgotpassword)
- [AuthGuard](#authguard)
- [AuthLogin](#authlogin)
- [AuthRegister](#authregister)
- [AuthResetPassword](#authresetpassword)
- [AuthSlider](#authslider)
- [AutoComplete](#autocomplete)
- [AutocompleteForms](#autocompleteforms)
- [AutoGrid](#autogrid)
- [AutoStopEditComponent](#autostopeditcomponent)
- [Avatar](#avatar)
- [AvatarUpload](#avatarupload)
- [AwsCognitoLogin](#awscognitologin)
- [AWSCognitoProvider](#awscognitoprovider)
- [AWSCognitoRegister](#awscognitoregister)
- [BackgroundPattern1](#backgroundpattern1)
- [BackgroundPattern2](#backgroundpattern2)
- [Backlogs](#backlogs)
- [BajajAreaChartCard](#bajajareachartcard)
- [BalanceBreakdownCard](#balancebreakdowncard)
- [BasicGrid](#basicgrid)
- [BasicGrouping](#basicgrouping)
- [BasicGroupingDemo](#basicgroupingdemo)
- [BasicRowEditingGrid](#basicroweditinggrid)
- [BasicSlider](#basicslider)
- [BasicWizard](#basicwizard)
- [BillCard](#billcard)
- [Board](#board)
- [Body](#body)
- [BorderRadius](#borderradius)
- [BoxContainer](#boxcontainer)
- [Breadcrumbs](#breadcrumbs)
- [BTitle](#btitle)
- [Card](#card)
- [CardSecondaryAction](#cardsecondaryaction)
- [Chart](#chart)
- [CheckboxForms](#checkboxforms)
- [CheckMail](#checkmail)
- [Chip](#chip)
- [CircularCountdown](#circularcountdown)
- [ClipboardPage](#clipboardpage)
- [CodeVerification](#codeverification)
- [ColorBox](#colorbox)
- [ColorInput](#colorinput)
- [ColorVariants](#colorvariants)
- [ColumnGroups](#columngroups)
- [ColumnMenu](#columnmenu)
- [ColumnMenuDemu](#columnmenudemu)
- [Columns](#columns)
- [ColumnsGrid](#columnsgrid)
- [ColumnsLayouts](#columnslayouts)
- [ColumnVirtualization](#columnvirtualization)
- [ColumnVirtualizationGrid](#columnvirtualizationgrid)
- [ColumnVisibility](#columnvisibility)
- [ColumnVisibilityPanel](#columnvisibilitypanel)
- [ComingSoon1](#comingsoon1)
- [ComingSoon2](#comingsoon2)
- [ComingSoonSlider](#comingsoonslider)
- [ComplexGrid](#complexgrid)
- [ComponentsOverrides](#componentsoverrides)
- [CompositionPieCard](#compositionpiecard)
- [ConfigProvider](#configprovider)
- [ContactCard](#contactcard)
- [ContactList](#contactlist)
- [ConversionsChartCard](#conversionschartcard)
- [CooldownTable](#cooldowntable)
- [CSVExport](#csvexport)
- [CustomColumnMenu](#customcolumnmenu)
- [CustomComponent](#customcomponent)
- [CustomDateTime](#customdatetime)
- [CustomEditComponent](#customeditcomponent)
- [CustomerSatisfactionCard](#customersatisfactioncard)
- [Customization](#customization)
- [CustomizationDemo](#customizationdemo)
- [CustomizedTables](#customizedtables)
- [CustomMenu](#custommenu)
- [CustomNotistack](#customnotistack)
- [CustomShadowBox](#customshadowbox)
- [CustomTabPanel](#customtabpanel)
- [CustomUserItem](#customuseritem)
- [CycloneRunSection](#cyclonerunsection)
- [Dashboard](#dashboard)
- [DashboardAnalytics](#dashboardanalytics)
- [DashboardDefault](#dashboarddefault)
- [DashboardGrid](#dashboardgrid)
- [DashboardToggle](#dashboardtoggle)
- [DashRowContainer](#dashrowcontainer)
- [DatabaseViewer](#databaseviewer)
- [DataCard](#datacard)
- [DataGridBasic](#datagridbasic)
- [DateTime](#datetime)
- [Dense](#dense)
- [DenseTable](#densetable)
- [DisableColumnMenu](#disablecolumnmenu)
- [DisableSlider](#disableslider)
- [DisableStopEditModeOnFocusOut](#disablestopeditmodeonfocusout)
- [DismissSnackBar](#dismisssnackbar)
- [DonutCountdown](#donutcountdown)
- [Dropzone](#dropzone)
- [EarningCard](#earningcard)
- [EditableColumn](#editablecolumn)
- [EditColumn](#editcolumn)
- [EditItem](#edititem)
- [Editor](#editor)
- [EditStory](#editstory)
- [ElevationScroll](#elevationscroll)
- [EnhancedTable](#enhancedtable)
- [EnhancedTableHead](#enhancedtablehead)
- [EnhancedTableToolbar](#enhancedtabletoolbar)
- [Error](#error)
- [ErrorBoundary](#errorboundary)
- [ExcludeHiddenColumn](#excludehiddencolumn)
- [FeedsCard](#feedscard)
- [FilesPreview](#filespreview)
- [FirebaseLogin](#firebaselogin)
- [FirebaseProvider](#firebaseprovider)
- [FirebaseRegister](#firebaseregister)
- [FirebaseSocial](#firebasesocial)
- [FloatingCart](#floatingcart)
- [FollowerCard](#followercard)
- [FontFamilyPage](#fontfamilypage)
- [Footer](#footer)
- [Forbidden](#forbidden)
- [ForgotPassword](#forgotpassword)
- [FormControl](#formcontrol)
- [FormControlSelect](#formcontrolselect)
- [FormRow](#formrow)
- [FormsValidation](#formsvalidation)
- [FormsWizard](#formswizard)
- [FriendRequestCard](#friendrequestcard)
- [FriendsCard](#friendscard)
- [FrmAutocomplete](#frmautocomplete)
- [FullFeaturedCrudGrid](#fullfeaturedcrudgrid)
- [FullScreen](#fullscreen)
- [FullWidthPaper](#fullwidthpaper)
- [FunCard](#funcard)
- [GalleryCard](#gallerycard)
- [GridSection](#gridsection)
- [GridSlot](#gridslot)
- [GridSystem](#gridsystem)
- [GrowTransition](#growtransition)
- [GuestGuard](#guestguard)
- [Header](#header)
- [HeaderAvatar](#headeravatar)
- [HeaderWithIcon](#headerwithicon)
- [HedgeEvaluator](#hedgeevaluator)
- [HedgeReportPage](#hedgereportpage)
- [HideDuration](#hideduration)
- [HideMenuItem](#hidemenuitem)
- [HorizontalBar](#horizontalbar)
- [HoverDataCard](#hoverdatacard)
- [HoverSocialCard](#hoversocialcard)
- [IconGridCard](#icongridcard)
- [IconNumberCard](#iconnumbercard)
- [IconVariants](#iconvariants)
- [IconVariantsContent](#iconvariantscontent)
- [ImageList](#imagelist)
- [ImagePlaceholder](#imageplaceholder)
- [IncomingRequests](#incomingrequests)
- [InitialState](#initialstate)
- [InlineEditing](#inlineediting)
- [InputFilled](#inputfilled)
- [InputLabel](#inputlabel)
- [InstantFeedback](#instantfeedback)
- [IsCellEditableGrid](#iscelleditablegrid)
- [Item](#item)
- [ItemComment](#itemcomment)
- [ItemDetails](#itemdetails)
- [Items](#items)
- [JupiterPage](#jupiterpage)
- [JWTLogin](#jwtlogin)
- [JWTProvider](#jwtprovider)
- [JWTRegister](#jwtregister)
- [KanbanBacklogs](#kanbanbacklogs)
- [KanbanBoard](#kanbanboard)
- [KanbanPage](#kanbanpage)
- [LabelSlider](#labelslider)
- [LandscapeDateTime](#landscapedatetime)
- [LatestCustomers](#latestcustomers)
- [LatestMessages](#latestmessages)
- [LatestOrder](#latestorder)
- [LatestPosts](#latestposts)
- [Layout](#layout)
- [Layouts](#layouts)
- [LinearProgressWithLabel](#linearprogresswithlabel)
- [LinkedIn](#linkedin)
- [LiqRow](#liqrow)
- [LiquidationBars](#liquidationbars)
- [LiquidationBarsCard](#liquidationbarscard)
- [LiquidationDistanceIcon](#liquidationdistanceicon)
- [LiquidationMonitorCard](#liquidationmonitorcard)
- [ListItemWrapper](#listitemwrapper)
- [Loadable](#loadable)
- [Loader](#loader)
- [Locales](#locales)
- [LocalizationSection](#localizationsection)
- [LogConsole](#logconsole)
- [Login](#login)
- [LoginForms](#loginforms)
- [LoginProvider](#loginprovider)
- [Logo](#logo)
- [LogoSection](#logosection)
- [LS_KEY](#ls_key)
- [MailerSubscriber](#mailersubscriber)
- [MainCard](#maincard)
- [MainLayout](#mainlayout)
- [MaintenanceComingSoon1](#maintenancecomingsoon1)
- [MaintenanceComingSoon2](#maintenancecomingsoon2)
- [MaintenanceError](#maintenanceerror)
- [MaintenanceError500](#maintenanceerror500)
- [MaintenanceForbidden](#maintenanceforbidden)
- [MaintenanceUnderConstruction](#maintenanceunderconstruction)
- [MarketChartCard](#marketchartcard)
- [MarketMonitorCard](#marketmonitorcard)
- [MarketMovementCard](#marketmovementcard)
- [MarketsPanel](#marketspanel)
- [MaskPage](#maskpage)
- [MaxSnackbar](#maxsnackbar)
- [MeetIcon](#meeticon)
- [MegaMenuBanner](#megamenubanner)
- [MegaMenuSection](#megamenusection)
- [MenuCard](#menucard)
- [MenuCloseComponent](#menuclosecomponent)
- [MenuList](#menulist)
- [MenuOrientationPage](#menuorientationpage)
- [MinimalLayout](#minimallayout)
- [MobileSearch](#mobilesearch)
- [MobileSection](#mobilesection)
- [Modal](#modal)
- [MonitorManager](#monitormanager)
- [MonitorManagerPage](#monitormanagerpage)
- [MonitorUpdateBar](#monitorupdatebar)
- [MultiFileUpload](#multifileupload)
- [MultipleBreakPoints](#multiplebreakpoints)
- [NameEditInputCell](#nameeditinputcell)
- [NavCollapse](#navcollapse)
- [NavGroup](#navgroup)
- [NavigationScroll](#navigationscroll)
- [NavItem](#navitem)
- [NavMotion](#navmotion)
- [NestedGrid](#nestedgrid)
- [NewCustomers](#newcustomers)
- [NotificationList](#notificationlist)
- [NotificationSection](#notificationsection)
- [Notistack](#notistack)
- [OperationsBar](#operationsbar)
- [OrderForm](#orderform)
- [OrgChartPage](#orgchartpage)
- [OverrideMenu](#overridemenu)
- [OverviewPage](#overviewpage)
- [Palette](#palette)
- [ParsingValues](#parsingvalues)
- [PaymentForm](#paymentform)
- [PerfChip](#perfchip)
- [PerformanceGraphCard](#performancegraphcard)
- [PlaceholderContent](#placeholdercontent)
- [PopularCard](#popularcard)
- [PopupSlider](#popupslider)
- [PortfolioBar](#portfoliobar)
- [PortfolioSessionCard](#portfoliosessioncard)
- [PositioningSnackbar](#positioningsnackbar)
- [PositionListCard](#positionlistcard)
- [PositionPieCard](#positionpiecard)
- [PositionsCell](#positionscell)
- [PositionsPage](#positionspage)
- [PositionsPanel](#positionspanel)
- [PositionsTable](#positionstable)
- [PositionsTableCard](#positionstablecard)
- [PositionTableCard](#positiontablecard)
- [PresetColorBox](#presetcolorbox)
- [PresetColorPage](#presetcolorpage)
- [PreventDuplicate](#preventduplicate)
- [ProductCard](#productcard)
- [ProductPlaceholder](#productplaceholder)
- [ProductReview](#productreview)
- [ProductSales](#productsales)
- [ProfitEmojiIcon](#profitemojiicon)
- [ProfitMonitorCard](#profitmonitorcard)
- [ProfitRiskHeaderBadges](#profitriskheaderbadges)
- [ProjectTable](#projecttable)
- [ProjectTaskCard](#projecttaskcard)
- [ProviderAccordion](#provideraccordion)
- [QuickFilter](#quickfilter)
- [QuickFilteringCustomLogic](#quickfilteringcustomlogic)
- [QuickFilteringInitialize](#quickfilteringinitialize)
- [QuickImportStarWars](#quickimportstarwars)
- [QuoteCard](#quotecard)
- [RadioGroupForms](#radiogroupforms)
- [RatingEditInputCell](#ratingeditinputcell)
- [RecaptchaPage](#recaptchapage)
- [RecentTickets](#recenttickets)
- [Register](#register)
- [RejectionFiles](#rejectionfiles)
- [ReorderMenu](#reordermenu)
- [ReportCard](#reportcard)
- [ResetPassword](#resetpassword)
- [RevenueCard](#revenuecard)
- [RevenueChartCard](#revenuechartcard)
- [Review](#review)
- [RoundIconCard](#roundiconcard)
- [Row](#row)
- [RTLLayout](#rtllayout)
- [SalesLineChartCard](#saleslinechartcard)
- [SatisfactionChartCard](#satisfactionchartcard)
- [SaveRestoreState](#saverestorestate)
- [SearchSection](#searchsection)
- [Section](#section)
- [SelectEditInputCell](#selecteditinputcell)
- [SelectForms](#selectforms)
- [SendCard](#sendcard)
- [SeoChartCard](#seochartcard)
- [ServerModal](#servermodal)
- [ServerSidePersistence](#serversidepersistence)
- [SettingsSection](#settingssection)
- [ShadowBox](#shadowbox)
- [Sidebar](#sidebar)
- [SidebarDrawer](#sidebardrawer)
- [SideIconCard](#sideiconcard)
- [SidePanelWidthSlider](#sidepanelwidthslider)
- [SimpleModal](#simplemodal)
- [SimpleTree](#simpletree)
- [SingleFileUpload](#singlefileupload)
- [SkypeIcon](#skypeicon)
- [Slider](#slider)
- [Snackbar](#snackbar)
- [SnackBarAction](#snackbaraction)
- [Sonic](#sonic)
- [SonicLabsPage](#soniclabspage)
- [SonicMonitorCard](#sonicmonitorcard)
- [SpacingGrid](#spacinggrid)
- [StartEditButtonGrid](#starteditbuttongrid)
- [StatCard](#statcard)
- [StatusCard](#statuscard)
- [StatusCell](#statuscell)
- [StatusRail](#statusrail)
- [StepCard](#stepcard)
- [StepSlider](#stepslider)
- [StickyActionBar](#stickyactionbar)
- [StickyHeadTable](#stickyheadtable)
- [StoryComment](#storycomment)
- [SubCard](#subcard)
- [SupabaseLogin](#supabaselogin)
- [SupabaseRegister](#supabaseregister)
- [SupabseProvider](#supabseprovider)
- [SwapsTab](#swapstab)
- [TableBasic](#tablebasic)
- [TableCollapsible](#tablecollapsible)
- [TableDataGrid](#tabledatagrid)
- [TasksCard](#taskscard)
- [TeamMembers](#teammembers)
- [TextFieldPage](#textfieldpage)
- [ThemeCustomization](#themecustomization)
- [ThemeLab](#themelab)
- [ThemeLabPage](#themelabpage)
- [ThemeModeLayout](#thememodelayout)
- [ThemeModeSection](#thememodesection)
- [ThresholdsTable](#thresholdstable)
- [ThresholdTable](#thresholdtable)
- [TimerSection](#timersection)
- [ToDoList](#todolist)
- [Toolbar](#toolbar)
- [Tooltip](#tooltip)
- [TopCell](#topcell)
- [TopTokensChips](#toptokenschips)
- [TotalGrowthBarChart](#totalgrowthbarchart)
- [TotalIncomeCard](#totalincomecard)
- [TotalIncomeDarkCard](#totalincomedarkcard)
- [TotalIncomeLightCard](#totalincomelightcard)
- [TotalLineChartCard](#totallinechartcard)
- [TotalOrderLineChartCard](#totalorderlinechartcard)
- [TotalRevenue](#totalrevenue)
- [TotalValueCard](#totalvaluecard)
- [TraderBar](#traderbar)
- [TraderCard](#tradercard)
- [TraderEnhancedTable](#traderenhancedtable)
- [TraderEnhancedTableHead](#traderenhancedtablehead)
- [TraderFactoryPage](#traderfactorypage)
- [TraderFormDrawer](#traderformdrawer)
- [TraderListCard](#traderlistcard)
- [TraderShopIndex](#tradershopindex)
- [TraderShopList](#tradershoplist)
- [TrafficSources](#trafficsources)
- [TransactionCard](#transactioncard)
- [TransitionBar](#transitionbar)
- [Transitions](#transitions)
- [TransitionSlideDown](#transitionslidedown)
- [TransitionSlideLeft](#transitionslideleft)
- [TransitionSlideRight](#transitionslideright)
- [TransitionSlideUp](#transitionslideup)
- [TreeCard](#treecard)
- [Typography](#typography)
- [UIButton](#uibutton)
- [UICheckbox](#uicheckbox)
- [UIColor](#uicolor)
- [UIRadio](#uiradio)
- [UISwitch](#uiswitch)
- [UnderConstruction](#underconstruction)
- [UpgradePlanCard](#upgradeplancard)
- [UseGridSelector](#usegridselector)
- [UserActivity](#useractivity)
- [UserCountCard](#usercountcard)
- [UserDetailsCard](#userdetailscard)
- [UserProfileCard](#userprofilecard)
- [UserSimpleCard](#usersimplecard)
- [UserStory](#userstory)
- [UtilitiesShadow](#utilitiesshadow)
- [ValidateServerNameGrid](#validateservernamegrid)
- [ValidationWizard](#validationwizard)
- [ValueParserSetterGrid](#valueparsersettergrid)
- [ValueToCollateralChartCard](#valuetocollateralchartcard)
- [VerifiedCell](#verifiedcell)
- [VerifiedSolCell](#verifiedsolcell)
- [VerifiedStatusCell](#verifiedstatuscell)
- [VerticalMonitorSummaryCard](#verticalmonitorsummarycard)
- [VerticalSlider](#verticalslider)
- [ViewOnlyAlert](#viewonlyalert)
- [ViewRendererDateTime](#viewrendererdatetime)
- [ViewsDateTimePicker](#viewsdatetimepicker)
- [VisibleColumnsModelControlled](#visiblecolumnsmodelcontrolled)
- [VisibleColumnsModelInitialState](#visiblecolumnsmodelinitialstate)
- [VolumeSlider](#volumeslider)
- [WalletCard](#walletcard)
- [WalletFormModal](#walletformmodal)
- [WalletManager](#walletmanager)
- [WalletManagerPage](#walletmanagerpage)
- [WalletPieCard](#walletpiecard)
- [WalletTable](#wallettable)
- [WeatherCard](#weathercard)
- [WidgetData](#widgetdata)
- [WidgetStatistics](#widgetstatistics)
- [WrappedComponent](#wrappedcomponent)
- [XComSettings](#xcomsettings)
- [XComSettingsPage](#xcomsettingspage)

## Accordion (`COMP_ACCORDION`)
- **File**: `frontend\src\ui-component\extended\Accordion.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `data` | `array` | no | — |
| `defaultExpandedId` | `oneOfType` | no | — |
| `expandIcon` | `node` | no | — |
| `square` | `bool` | no | — |
| `toggle` | `bool` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Accordion from "ui-component/extended/Accordion";

export default function Example() {
  return (
    <Accordion
    data={[]}
    defaultExpandedId={/* TODO */}
    expandIcon="example"
    square={false}
    toggle={false}
    />
  );
}
```
---
## ActionBar (`COMP_ACTIONBAR`)
- **File**: `frontend\src\views\forms\layouts\ActionBar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ActionBar from "views/forms/layouts/ActionBar";

export default function Example() {
  return (
    <ActionBar
    />
  );
}
```
---
## ActionsCell (`COMP_ACTIONSCELL`)
- **File**: `frontend\src\ui-component\wallet\WalletTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ActionsCell from "ui-component/wallet/WalletTable";

export default function Example() {
  return (
    <ActionsCell
    />
  );
}
```
---
## ActiveTickets (`COMP_ACTIVETICKETS`)
- **File**: `frontend\src\views\widget\Data\ActiveTickets.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ActiveTickets from "views/widget/Data/ActiveTickets";

export default function Example() {
  return (
    <ActiveTickets
    />
  );
}
```
---
## AddColumn (`COMP_ADDCOLUMN`)
- **File**: `frontend\src\views\kanban\Board\AddColumn.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AddColumn from "views/kanban/Board/AddColumn";

export default function Example() {
  return (
    <AddColumn
    />
  );
}
```
---
## AddItem (`COMP_ADDITEM`)
- **File**: `frontend\src\views\kanban\Backlogs\AddItem.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `columnId` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AddItem from "views/kanban/Backlogs/AddItem";

export default function Example() {
  return (
    <AddItem
    columnId="example"
    />
  );
}
```
---
## AddItemComment (`COMP_ADDITEMCOMMENT`)
- **File**: `frontend\src\views\kanban\Board\AddItemComment.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `itemId` | `oneOfType` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AddItemComment from "views/kanban/Board/AddItemComment";

export default function Example() {
  return (
    <AddItemComment
    itemId={/* TODO */}
    />
  );
}
```
---
## AddMenuItem (`COMP_ADDMENUITEM`)
- **File**: `frontend\src\views\forms\data-grid\ColumnMenu\AddMenuItem.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AddMenuItem from "views/forms/data-grid/ColumnMenu/AddMenuItem";

export default function Example() {
  return (
    <AddMenuItem
    />
  );
}
```
---
## AddressCell (`COMP_ADDRESSCELL`)
- **File**: `frontend\src\ui-component\wallet\WalletTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AddressCell from "ui-component/wallet/WalletTable";

export default function Example() {
  return (
    <AddressCell
    />
  );
}
```
---
## AddressForm (`COMP_ADDRESSFORM`)
- **File**: `frontend\src\views\forms\forms-wizard\BasicWizard\AddressForm.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `shippingData` | `any` | no | — |
| `setShippingData` | `func` | no | — |
| `handleNext` | `func` | no | — |
| `setErrorIndex` | `func` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AddressForm from "views/forms/forms-wizard/BasicWizard/AddressForm";

export default function Example() {
  return (
    <AddressForm
    shippingData={{}}
    setShippingData={/* TODO */}
    handleNext={/* TODO */}
    setErrorIndex={/* TODO */}
    />
  );
}
```
---
## AddStory (`COMP_ADDSTORY`)
- **File**: `frontend\src\views\kanban\Backlogs\AddStory.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `open` | `bool` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AddStory from "views/kanban/Backlogs/AddStory";

export default function Example() {
  return (
    <AddStory
    open={false}
    />
  );
}
```
---
## AddStoryComment (`COMP_ADDSTORYCOMMENT`)
- **File**: `frontend\src\views\kanban\Backlogs\AddStoryComment.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `storyId` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AddStoryComment from "views/kanban/Backlogs/AddStoryComment";

export default function Example() {
  return (
    <AddStoryComment
    storyId="example"
    />
  );
}
```
---
## AddThresholdDialog (`COMP_ADDTHRESHOLDDIALOG`)
- **File**: `frontend\src\views\alertThresholds\AddThresholdDialog.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AddThresholdDialog from "views/alertThresholds/AddThresholdDialog";

export default function Example() {
  return (
    <AddThresholdDialog
    />
  );
}
```
---
## AlertColumnDelete (`COMP_ALERTCOLUMNDELETE`)
- **File**: `frontend\src\views\kanban\Board\AlertColumnDelete.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `title` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AlertColumnDelete from "views/kanban/Board/AlertColumnDelete";

export default function Example() {
  return (
    <AlertColumnDelete
    title="example"
    />
  );
}
```
---
## AlertItemDelete (`COMP_ALERTITEMDELETE`)
- **File**: `frontend\src\views\kanban\Board\AlertItemDelete.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `title` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AlertItemDelete from "views/kanban/Board/AlertItemDelete";

export default function Example() {
  return (
    <AlertItemDelete
    title="example"
    />
  );
}
```
---
## AlertStoryDelete (`COMP_ALERTSTORYDELETE`)
- **File**: `frontend\src\views\kanban\Backlogs\AlertStoryDelete.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `title` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AlertStoryDelete from "views/kanban/Backlogs/AlertStoryDelete";

export default function Example() {
  return (
    <AlertStoryDelete
    title="example"
    />
  );
}
```
---
## AlertThresholdsPage (`COMP_ALERTTHRESHOLDSPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AlertThresholdsPage from "routes/MainRoutes";

export default function Example() {
  return (
    <AlertThresholdsPage
    />
  );
}
```
---
## Analytics (`COMP_ANALYTICS`)
- **File**: `frontend\src\views\dashboard\Analytics\index - Copy (2).jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Analytics from "views/dashboard/Analytics/index - Copy (2)";

export default function Example() {
  return (
    <Analytics
    />
  );
}
```
---
## AnalyticsChartCard (`COMP_ANALYTICSCHARTCARD`)
- **File**: `frontend\src\ui-component\cards\AnalyticsChartCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `title` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AnalyticsChartCard from "ui-component/cards/AnalyticsChartCard";

export default function Example() {
  return (
    <AnalyticsChartCard
    title={{}}
    />
  );
}
```
---
## AnimateButton (`COMP_ANIMATEBUTTON`)
- **File**: `frontend\src\ui-component\extended\AnimateButton.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |
| `type` | `oneOf` | no | — |
| `direction` | `oneOf` | no | — |
| `offset` | `number` | no | — |
| `scale` | `object` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AnimateButton from "ui-component/extended/AnimateButton";

export default function Example() {
  return (
    <AnimateButton
    children="example"
    type={/* TODO */}
    direction={/* TODO */}
    offset={0}
    scale={{}}
    />
  );
}
```
---
## Animation (`COMP_ANIMATION`)
- **File**: `frontend\src\views\utilities\Animation.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Animation from "views/utilities/Animation";

export default function Example() {
  return (
    <Animation
    />
  );
}
```
---
## ApexAreaChart (`COMP_APEXAREACHART`)
- **File**: `frontend\src\views\forms\chart\Apexchart\ApexAreaChart.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ApexAreaChart from "views/forms/chart/Apexchart/ApexAreaChart";

export default function Example() {
  return (
    <ApexAreaChart
    />
  );
}
```
---
## ApexBarChart (`COMP_APEXBARCHART`)
- **File**: `frontend\src\views\forms\chart\Apexchart\ApexBarChart.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ApexBarChart from "views/forms/chart/Apexchart/ApexBarChart";

export default function Example() {
  return (
    <ApexBarChart
    />
  );
}
```
---
## Apexchart (`COMP_APEXCHART`)
- **File**: `frontend\src\views\forms\chart\Apexchart\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Apexchart from "views/forms/chart/Apexchart/index";

export default function Example() {
  return (
    <Apexchart
    />
  );
}
```
---
## ApexColumnChart (`COMP_APEXCOLUMNCHART`)
- **File**: `frontend\src\views\forms\chart\Apexchart\ApexColumnChart.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ApexColumnChart from "views/forms/chart/Apexchart/ApexColumnChart";

export default function Example() {
  return (
    <ApexColumnChart
    />
  );
}
```
---
## ApexLineChart (`COMP_APEXLINECHART`)
- **File**: `frontend\src\views\forms\chart\Apexchart\ApexLineChart.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ApexLineChart from "views/forms/chart/Apexchart/ApexLineChart";

export default function Example() {
  return (
    <ApexLineChart
    />
  );
}
```
---
## ApexMixedChart (`COMP_APEXMIXEDCHART`)
- **File**: `frontend\src\views\forms\chart\Apexchart\ApexMixedChart.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ApexMixedChart from "views/forms/chart/Apexchart/ApexMixedChart";

export default function Example() {
  return (
    <ApexMixedChart
    />
  );
}
```
---
## ApexPieChart (`COMP_APEXPIECHART`)
- **File**: `frontend\src\views\forms\chart\Apexchart\ApexPieChart.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ApexPieChart from "views/forms/chart/Apexchart/ApexPieChart";

export default function Example() {
  return (
    <ApexPieChart
    />
  );
}
```
---
## ApexPolarChart (`COMP_APEXPOLARCHART`)
- **File**: `frontend\src\views\forms\chart\Apexchart\ApexPolarChart.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ApexPolarChart from "views/forms/chart/Apexchart/ApexPolarChart";

export default function Example() {
  return (
    <ApexPolarChart
    />
  );
}
```
---
## ApexRedialBarChart (`COMP_APEXREDIALBARCHART`)
- **File**: `frontend\src\views\forms\chart\Apexchart\ApexRedialChart.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ApexRedialBarChart from "views/forms/chart/Apexchart/ApexRedialChart";

export default function Example() {
  return (
    <ApexRedialBarChart
    />
  );
}
```
---
## App (`COMP_APP`)
- **File**: `frontend\src\App.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import App from "App";

export default function Example() {
  return (
    <App
    />
  );
}
```
---
## AppBar (`COMP_APPBAR`)
- **File**: `frontend\src\ui-component\extended\AppBar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AppBar from "ui-component/extended/AppBar";

export default function Example() {
  return (
    <AppBar
    />
  );
}
```
---
## AppGrid (`COMP_APPGRID`)
- **File**: `frontend\src\components\AppGrid.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AppGrid from "components/AppGrid";

export default function Example() {
  return (
    <AppGrid
    />
  );
}
```
---
## ApplicationSales (`COMP_APPLICATIONSALES`)
- **File**: `frontend\src\views\widget\Data\ApplicationSales.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ApplicationSales from "views/widget/Data/ApplicationSales";

export default function Example() {
  return (
    <ApplicationSales
    />
  );
}
```
---
## AskConfirmationBeforeSave (`COMP_ASKCONFIRMATIONBEFORESAVE`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\ConfirmationSave.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AskConfirmationBeforeSave from "views/forms/data-grid/InLineEditing/ConfirmationSave";

export default function Example() {
  return (
    <AskConfirmationBeforeSave
    />
  );
}
```
---
## AssetLogo (`COMP_ASSETLOGO`)
- **File**: `frontend\src\components\AssetLogo.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AssetLogo from "components/AssetLogo";

export default function Example() {
  return (
    <AssetLogo
    />
  );
}
```
---
## AttachmentCard (`COMP_ATTACHMENTCARD`)
- **File**: `frontend\src\ui-component\cards\AttachmentCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `title` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AttachmentCard from "ui-component/cards/AttachmentCard";

export default function Example() {
  return (
    <AttachmentCard
    title="example"
    />
  );
}
```
---
## Auth0ContextProvider (`COMP_AUTH0CONTEXTPROVIDER`)
- **File**: `frontend\src\contexts\Auth0Context.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Auth0ContextProvider from "contexts/Auth0Context";

export default function Example() {
  return (
    <Auth0ContextProvider
    children="example"
    />
  );
}
```
---
## Auth0Login (`COMP_AUTH0LOGIN`)
- **File**: `frontend\src\views\pages\authentication\auth0\AuthLogin.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Auth0Login from "views/pages/authentication/auth0/AuthLogin";

export default function Example() {
  return (
    <Auth0Login
    />
  );
}
```
---
## Auth0Provider (`COMP_AUTH0PROVIDER`)
- **File**: `frontend\src\contexts\Auth0Context.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Auth0Provider from "contexts/Auth0Context";

export default function Example() {
  return (
    <Auth0Provider
    children="example"
    />
  );
}
```
---
## Auth0Register (`COMP_AUTH0REGISTER`)
- **File**: `frontend\src\views\pages\authentication\auth0\AuthRegister.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Auth0Register from "views/pages/authentication/auth0/AuthRegister";

export default function Example() {
  return (
    <Auth0Register
    />
  );
}
```
---
## AuthCardWrapper (`COMP_AUTHCARDWRAPPER`)
- **File**: `frontend\src\views\pages\authentication\AuthCardWrapper.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AuthCardWrapper from "views/pages/authentication/AuthCardWrapper";

export default function Example() {
  return (
    <AuthCardWrapper
    children={{}}
    />
  );
}
```
---
## AuthCheckMail (`COMP_AUTHCHECKMAIL`)
- **File**: `frontend\src\routes\LoginRoutes.jsx`
- **Used by routes**: `/`, `/check-mail`, `/code-verification`, `/forgot-password`, `/login`, `/register`, `/reset-password`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AuthCheckMail from "routes/LoginRoutes";

export default function Example() {
  return (
    <AuthCheckMail
    />
  );
}
```
---
## AuthCodeVerification (`COMP_AUTHCODEVERIFICATION`)
- **File**: `frontend\src\routes\LoginRoutes.jsx`
- **Used by routes**: `/`, `/check-mail`, `/code-verification`, `/forgot-password`, `/login`, `/register`, `/reset-password`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AuthCodeVerification from "routes/LoginRoutes";

export default function Example() {
  return (
    <AuthCodeVerification
    />
  );
}
```
---
## AuthFooter (`COMP_AUTHFOOTER`)
- **File**: `frontend\src\ui-component\cards\AuthFooter.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AuthFooter from "ui-component/cards/AuthFooter";

export default function Example() {
  return (
    <AuthFooter
    />
  );
}
```
---
## AuthForgotPassword (`COMP_AUTHFORGOTPASSWORD`)
- **File**: `frontend\src\routes\LoginRoutes.jsx`
- **Used by routes**: `/`, `/check-mail`, `/code-verification`, `/forgot-password`, `/login`, `/register`, `/reset-password`

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `link` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AuthForgotPassword from "routes/LoginRoutes";

export default function Example() {
  return (
    <AuthForgotPassword
    link="example"
    />
  );
}
```
---
## AuthGuard (`COMP_AUTHGUARD`)
- **File**: `frontend\src\utils\route-guard\AuthGuard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AuthGuard from "utils/route-guard/AuthGuard";

export default function Example() {
  return (
    <AuthGuard
    children={{}}
    />
  );
}
```
---
## AuthLogin (`COMP_AUTHLOGIN`)
- **File**: `frontend\src\routes\LoginRoutes.jsx`
- **Used by routes**: `/`, `/check-mail`, `/code-verification`, `/forgot-password`, `/login`, `/register`, `/reset-password`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AuthLogin from "routes/LoginRoutes";

export default function Example() {
  return (
    <AuthLogin
    />
  );
}
```
---
## AuthRegister (`COMP_AUTHREGISTER`)
- **File**: `frontend\src\routes\LoginRoutes.jsx`
- **Used by routes**: `/`, `/check-mail`, `/code-verification`, `/forgot-password`, `/login`, `/register`, `/reset-password`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AuthRegister from "routes/LoginRoutes";

export default function Example() {
  return (
    <AuthRegister
    />
  );
}
```
---
## AuthResetPassword (`COMP_AUTHRESETPASSWORD`)
- **File**: `frontend\src\routes\LoginRoutes.jsx`
- **Used by routes**: `/`, `/check-mail`, `/code-verification`, `/forgot-password`, `/login`, `/register`, `/reset-password`

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `link` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AuthResetPassword from "routes/LoginRoutes";

export default function Example() {
  return (
    <AuthResetPassword
    link="example"
    />
  );
}
```
---
## AuthSlider (`COMP_AUTHSLIDER`)
- **File**: `frontend\src\ui-component\cards\AuthSlider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `items` | `array` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AuthSlider from "ui-component/cards/AuthSlider";

export default function Example() {
  return (
    <AuthSlider
    items={[]}
    />
  );
}
```
---
## AutoComplete (`COMP_AUTOCOMPLETE`)
- **File**: `frontend\src\views\forms\components\AutoComplete.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AutoComplete from "views/forms/components/AutoComplete";

export default function Example() {
  return (
    <AutoComplete
    />
  );
}
```
---
## AutocompleteForms (`COMP_AUTOCOMPLETEFORMS`)
- **File**: `frontend\src\views\forms\forms-validation\AutocompleteForms.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AutocompleteForms from "views/forms/forms-validation/AutocompleteForms";

export default function Example() {
  return (
    <AutocompleteForms
    />
  );
}
```
---
## AutoGrid (`COMP_AUTOGRID`)
- **File**: `frontend\src\views\utilities\Grid\AutoGrid.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AutoGrid from "views/utilities/Grid/AutoGrid";

export default function Example() {
  return (
    <AutoGrid
    />
  );
}
```
---
## AutoStopEditComponent (`COMP_AUTOSTOPEDITCOMPONENT`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\AutoStop.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AutoStopEditComponent from "views/forms/data-grid/InLineEditing/AutoStop";

export default function Example() {
  return (
    <AutoStopEditComponent
    />
  );
}
```
---
## Avatar (`COMP_AVATAR`)
- **File**: `frontend\src\ui-component\extended\Avatar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `className` | `string` | no | — |
| `color` | `string` | no | — |
| `outline` | `bool` | no | — |
| `size` | `oneOf` | no | — |
| `sx` | `any` | no | — |
| `others` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Avatar from "ui-component/extended/Avatar";

export default function Example() {
  return (
    <Avatar
    className="example"
    color="example"
    outline={false}
    size={/* TODO */}
    sx={{}}
    others={{}}
    />
  );
}
```
---
## AvatarUpload (`COMP_AVATARUPLOAD`)
- **File**: `frontend\src\ui-component\third-party\dropzone\Avatar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `error` | `any` | no | — |
| `file` | `array` | no | — |
| `setFieldValue` | `any` | no | — |
| `sx` | `any` | no | — |
| `other` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AvatarUpload from "ui-component/third-party/dropzone/Avatar";

export default function Example() {
  return (
    <AvatarUpload
    error={{}}
    file={[]}
    setFieldValue={{}}
    sx={{}}
    other={{}}
    />
  );
}
```
---
## AwsCognitoLogin (`COMP_AWSCOGNITOLOGIN`)
- **File**: `frontend\src\views\pages\authentication\aws\AuthLogin.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AwsCognitoLogin from "views/pages/authentication/aws/AuthLogin";

export default function Example() {
  return (
    <AwsCognitoLogin
    />
  );
}
```
---
## AWSCognitoProvider (`COMP_AWSCOGNITOPROVIDER`)
- **File**: `frontend\src\contexts\AWSCognitoContext.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AWSCognitoProvider from "contexts/AWSCognitoContext";

export default function Example() {
  return (
    <AWSCognitoProvider
    children="example"
    />
  );
}
```
---
## AWSCognitoRegister (`COMP_AWSCOGNITOREGISTER`)
- **File**: `frontend\src\views\pages\authentication\aws\AuthRegister.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import AWSCognitoRegister from "views/pages/authentication/aws/AuthRegister";

export default function Example() {
  return (
    <AWSCognitoRegister
    />
  );
}
```
---
## BackgroundPattern1 (`COMP_BACKGROUNDPATTERN1`)
- **File**: `frontend\src\ui-component\cards\BackgroundPattern1.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BackgroundPattern1 from "ui-component/cards/BackgroundPattern1";

export default function Example() {
  return (
    <BackgroundPattern1
    children="example"
    />
  );
}
```
---
## BackgroundPattern2 (`COMP_BACKGROUNDPATTERN2`)
- **File**: `frontend\src\ui-component\cards\BackgroundPattern2.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BackgroundPattern2 from "ui-component/cards/BackgroundPattern2";

export default function Example() {
  return (
    <BackgroundPattern2
    children="example"
    />
  );
}
```
---
## Backlogs (`COMP_BACKLOGS`)
- **File**: `frontend\src\views\kanban\Backlogs\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Backlogs from "views/kanban/Backlogs/index";

export default function Example() {
  return (
    <Backlogs
    />
  );
}
```
---
## BajajAreaChartCard (`COMP_BAJAJAREACHARTCARD`)
- **File**: `frontend\src\views\dashboard\Default\BajajAreaChartCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BajajAreaChartCard from "views/dashboard/Default/BajajAreaChartCard";

export default function Example() {
  return (
    <BajajAreaChartCard
    />
  );
}
```
---
## BalanceBreakdownCard (`COMP_BALANCEBREAKDOWNCARD`)
- **File**: `frontend\src\views\wallet\BalanceBreakdownCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BalanceBreakdownCard from "views/wallet/BalanceBreakdownCard";

export default function Example() {
  return (
    <BalanceBreakdownCard
    />
  );
}
```
---
## BasicGrid (`COMP_BASICGRID`)
- **File**: `frontend\src\views\utilities\Grid\BasicGrid.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BasicGrid from "views/utilities/Grid/BasicGrid";

export default function Example() {
  return (
    <BasicGrid
    />
  );
}
```
---
## BasicGrouping (`COMP_BASICGROUPING`)
- **File**: `frontend\src\views\forms\data-grid\ColumnGroups\BasicColumnGroup.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BasicGrouping from "views/forms/data-grid/ColumnGroups/BasicColumnGroup";

export default function Example() {
  return (
    <BasicGrouping
    />
  );
}
```
---
## BasicGroupingDemo (`COMP_BASICGROUPINGDEMO`)
- **File**: `frontend\src\views\forms\data-grid\ColumnGroups\BasicColumnGroup.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `Selected` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BasicGroupingDemo from "views/forms/data-grid/ColumnGroups/BasicColumnGroup";

export default function Example() {
  return (
    <BasicGroupingDemo
    Selected={{}}
    />
  );
}
```
---
## BasicRowEditingGrid (`COMP_BASICROWEDITINGGRID`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\EditableRow.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BasicRowEditingGrid from "views/forms/data-grid/InLineEditing/EditableRow";

export default function Example() {
  return (
    <BasicRowEditingGrid
    />
  );
}
```
---
## BasicSlider (`COMP_BASICSLIDER`)
- **File**: `frontend\src\views\forms\components\Slider\BasicSlider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BasicSlider from "views/forms/components/Slider/BasicSlider";

export default function Example() {
  return (
    <BasicSlider
    />
  );
}
```
---
## BasicWizard (`COMP_BASICWIZARD`)
- **File**: `frontend\src\views\forms\forms-wizard\BasicWizard\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BasicWizard from "views/forms/forms-wizard/BasicWizard/index";

export default function Example() {
  return (
    <BasicWizard
    />
  );
}
```
---
## BillCard (`COMP_BILLCARD`)
- **File**: `frontend\src\ui-component\cards\BillCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `primary` | `any` | no | — |
| `secondary` | `any` | no | — |
| `link` | `string` | no | — |
| `color` | `any` | no | — |
| `bg` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BillCard from "ui-component/cards/BillCard";

export default function Example() {
  return (
    <BillCard
    primary={{}}
    secondary={{}}
    link="example"
    color={{}}
    bg="example"
    />
  );
}
```
---
## Board (`COMP_BOARD`)
- **File**: `frontend\src\views\kanban\Board\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Board from "views/kanban/Board/index";

export default function Example() {
  return (
    <Board
    />
  );
}
```
---
## Body (`COMP_BODY`)
- **File**: `frontend\src\views\forms\plugins\Modal\SimpleModal.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `modalStyle` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Body from "views/forms/plugins/Modal/SimpleModal";

export default function Example() {
  return (
    <Body
    modalStyle={{}}
    />
  );
}
```
---
## BorderRadius (`COMP_BORDERRADIUS`)
- **File**: `frontend\src\layout\Customization\BorderRadius.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BorderRadius from "layout/Customization/BorderRadius";

export default function Example() {
  return (
    <BorderRadius
    />
  );
}
```
---
## BoxContainer (`COMP_BOXCONTAINER`)
- **File**: `frontend\src\layout\Customization\BoxContainer.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BoxContainer from "layout/Customization/BoxContainer";

export default function Example() {
  return (
    <BoxContainer
    />
  );
}
```
---
## Breadcrumbs (`COMP_BREADCRUMBS`)
- **File**: `frontend\src\ui-component\extended\Breadcrumbs.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `card` | `bool` | no | — |
| `custom` | `bool` | no | — |
| `divider` | `bool` | no | — |
| `heading` | `string` | no | — |
| `icon` | `bool` | no | — |
| `icons` | `bool` | no | — |
| `links` | `array` | no | — |
| `maxItems` | `number` | no | — |
| `rightAlign` | `bool` | no | — |
| `separator` | `any` | no | — |
| `IconChevronRight` | `any` | no | — |
| `title` | `bool` | no | — |
| `titleBottom` | `bool` | no | — |
| `sx` | `any` | no | — |
| `others` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Breadcrumbs from "ui-component/extended/Breadcrumbs";

export default function Example() {
  return (
    <Breadcrumbs
    card={false}
    custom={false}
    divider={false}
    heading="example"
    icon={false}
    icons={false}
    />
  );
}
```
---
## BTitle (`COMP_BTITLE`)
- **File**: `frontend\src\ui-component\extended\Breadcrumbs.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `title` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import BTitle from "ui-component/extended/Breadcrumbs";

export default function Example() {
  return (
    <BTitle
    title="example"
    />
  );
}
```
---
## Card (`COMP_CARD`)
- **File**: `frontend\src\views\forms\chart\OrgChart\Card.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `items` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Card from "views/forms/chart/OrgChart/Card";

export default function Example() {
  return (
    <Card
    items={{}}
    />
  );
}
```
---
## CardSecondaryAction (`COMP_CARDSECONDARYACTION`)
- **File**: `frontend\src\ui-component\cards\CardSecondaryAction.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `title` | `string` | no | — |
| `link` | `string` | no | — |
| `icon` | `oneOfType` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CardSecondaryAction from "ui-component/cards/CardSecondaryAction";

export default function Example() {
  return (
    <CardSecondaryAction
    title="example"
    link="example"
    icon={/* TODO */}
    />
  );
}
```
---
## Chart (`COMP_CHART`)
- **File**: `frontend\src\views\widget\Chart\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Chart from "views/widget/Chart/index";

export default function Example() {
  return (
    <Chart
    />
  );
}
```
---
## CheckboxForms (`COMP_CHECKBOXFORMS`)
- **File**: `frontend\src\views\forms\forms-validation\CheckboxForms.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CheckboxForms from "views/forms/forms-validation/CheckboxForms";

export default function Example() {
  return (
    <CheckboxForms
    />
  );
}
```
---
## CheckMail (`COMP_CHECKMAIL`)
- **File**: `frontend\src\views\pages\authentication\CheckMail.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CheckMail from "views/pages/authentication/CheckMail";

export default function Example() {
  return (
    <CheckMail
    />
  );
}
```
---
## Chip (`COMP_CHIP`)
- **File**: `frontend\src\themes\overrides\Chip.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Chip from "themes/overrides/Chip";

export default function Example() {
  return (
    <Chip
    />
  );
}
```
---
## CircularCountdown (`COMP_CIRCULARCOUNTDOWN`)
- **File**: `frontend\src\views\monitorManager\SonicMonitorCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CircularCountdown from "views/monitorManager/SonicMonitorCard";

export default function Example() {
  return (
    <CircularCountdown
    />
  );
}
```
---
## ClipboardPage (`COMP_CLIPBOARDPAGE`)
- **File**: `frontend\src\views\forms\plugins\Clipboard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ClipboardPage from "views/forms/plugins/Clipboard";

export default function Example() {
  return (
    <ClipboardPage
    />
  );
}
```
---
## CodeVerification (`COMP_CODEVERIFICATION`)
- **File**: `frontend\src\views\pages\authentication\CodeVerification.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CodeVerification from "views/pages/authentication/CodeVerification";

export default function Example() {
  return (
    <CodeVerification
    />
  );
}
```
---
## ColorBox (`COMP_COLORBOX`)
- **File**: `frontend\src\views\utilities\Color.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColorBox from "views/utilities/Color";

export default function Example() {
  return (
    <ColorBox
    />
  );
}
```
---
## ColorInput (`COMP_COLORINPUT`)
- **File**: `frontend\src\views\labs\ThemeLab.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColorInput from "views/labs/ThemeLab";

export default function Example() {
  return (
    <ColorInput
    />
  );
}
```
---
## ColorVariants (`COMP_COLORVARIANTS`)
- **File**: `frontend\src\ui-component\extended\notistack\ColorVariants.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColorVariants from "ui-component/extended/notistack/ColorVariants";

export default function Example() {
  return (
    <ColorVariants
    />
  );
}
```
---
## ColumnGroups (`COMP_COLUMNGROUPS`)
- **File**: `frontend\src\views\forms\data-grid\ColumnGroups\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColumnGroups from "views/forms/data-grid/ColumnGroups/index";

export default function Example() {
  return (
    <ColumnGroups
    />
  );
}
```
---
## ColumnMenu (`COMP_COLUMNMENU`)
- **File**: `frontend\src\views\forms\data-grid\ColumnMenu\ColumnMenu.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColumnMenu from "views/forms/data-grid/ColumnMenu/ColumnMenu";

export default function Example() {
  return (
    <ColumnMenu
    />
  );
}
```
---
## ColumnMenuDemu (`COMP_COLUMNMENUDEMU`)
- **File**: `frontend\src\views\forms\data-grid\ColumnMenu\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColumnMenuDemu from "views/forms/data-grid/ColumnMenu/index";

export default function Example() {
  return (
    <ColumnMenuDemu
    />
  );
}
```
---
## Columns (`COMP_COLUMNS`)
- **File**: `frontend\src\views\kanban\Board\Columns.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `column` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Columns from "views/kanban/Board/Columns";

export default function Example() {
  return (
    <Columns
    column={{}}
    />
  );
}
```
---
## ColumnsGrid (`COMP_COLUMNSGRID`)
- **File**: `frontend\src\views\utilities\Grid\ColumnsGrid.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColumnsGrid from "views/utilities/Grid/ColumnsGrid";

export default function Example() {
  return (
    <ColumnsGrid
    />
  );
}
```
---
## ColumnsLayouts (`COMP_COLUMNSLAYOUTS`)
- **File**: `frontend\src\views\forms\layouts\MultiColumnForms.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColumnsLayouts from "views/forms/layouts/MultiColumnForms";

export default function Example() {
  return (
    <ColumnsLayouts
    />
  );
}
```
---
## ColumnVirtualization (`COMP_COLUMNVIRTUALIZATION`)
- **File**: `frontend\src\views\forms\data-grid\ColumnVirtualization\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColumnVirtualization from "views/forms/data-grid/ColumnVirtualization/index";

export default function Example() {
  return (
    <ColumnVirtualization
    />
  );
}
```
---
## ColumnVirtualizationGrid (`COMP_COLUMNVIRTUALIZATIONGRID`)
- **File**: `frontend\src\views\forms\data-grid\ColumnVirtualization\Virtualization.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColumnVirtualizationGrid from "views/forms/data-grid/ColumnVirtualization/Virtualization";

export default function Example() {
  return (
    <ColumnVirtualizationGrid
    />
  );
}
```
---
## ColumnVisibility (`COMP_COLUMNVISIBILITY`)
- **File**: `frontend\src\views\forms\data-grid\ColumnVisibility\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColumnVisibility from "views/forms/data-grid/ColumnVisibility/index";

export default function Example() {
  return (
    <ColumnVisibility
    />
  );
}
```
---
## ColumnVisibilityPanel (`COMP_COLUMNVISIBILITYPANEL`)
- **File**: `frontend\src\views\forms\data-grid\ColumnVisibility\VisibilityPanel.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ColumnVisibilityPanel from "views/forms/data-grid/ColumnVisibility/VisibilityPanel";

export default function Example() {
  return (
    <ColumnVisibilityPanel
    />
  );
}
```
---
## ComingSoon1 (`COMP_COMINGSOON1`)
- **File**: `frontend\src\views\pages\maintenance\ComingSoon\ComingSoon1\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ComingSoon1 from "views/pages/maintenance/ComingSoon/ComingSoon1/index";

export default function Example() {
  return (
    <ComingSoon1
    />
  );
}
```
---
## ComingSoon2 (`COMP_COMINGSOON2`)
- **File**: `frontend\src\views\pages\maintenance\ComingSoon\ComingSoon2.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ComingSoon2 from "views/pages/maintenance/ComingSoon/ComingSoon2";

export default function Example() {
  return (
    <ComingSoon2
    />
  );
}
```
---
## ComingSoonSlider (`COMP_COMINGSOONSLIDER`)
- **File**: `frontend\src\views\pages\maintenance\ComingSoon\ComingSoon1\Slider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `handleClickOpen` | `func` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ComingSoonSlider from "views/pages/maintenance/ComingSoon/ComingSoon1/Slider";

export default function Example() {
  return (
    <ComingSoonSlider
    handleClickOpen={/* TODO */}
    />
  );
}
```
---
## ComplexGrid (`COMP_COMPLEXGRID`)
- **File**: `frontend\src\views\utilities\Grid\ComplexGrid.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ComplexGrid from "views/utilities/Grid/ComplexGrid";

export default function Example() {
  return (
    <ComplexGrid
    />
  );
}
```
---
## ComponentsOverrides (`COMP_COMPONENTSOVERRIDES`)
- **File**: `frontend\src\themes\overrides\index.js`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ComponentsOverrides from "themes/overrides/index";

export default function Example() {
  return (
    <ComponentsOverrides
    />
  );
}
```
---
## CompositionPieCard (`COMP_COMPOSITIONPIECARD`)
- **File**: `frontend\src\components\CompositionPieCard\CompositionPieCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `maxHeight` | `oneOfType` | no | — |
| `maxWidth` | `oneOfType` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CompositionPieCard from "components/CompositionPieCard/CompositionPieCard";

export default function Example() {
  return (
    <CompositionPieCard
    maxHeight={/* TODO */}
    maxWidth={/* TODO */}
    />
  );
}
```
---
## ConfigProvider (`COMP_CONFIGPROVIDER`)
- **File**: `frontend\src\contexts\ConfigContext.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ConfigProvider from "contexts/ConfigContext";

export default function Example() {
  return (
    <ConfigProvider
    children="example"
    />
  );
}
```
---
## ContactCard (`COMP_CONTACTCARD`)
- **File**: `frontend\src\ui-component\cards\ContactCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `avatar` | `any` | no | — |
| `contact` | `any` | no | — |
| `email` | `any` | no | — |
| `name` | `any` | no | — |
| `location` | `any` | no | — |
| `onActive` | `func` | no | — |
| `role` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ContactCard from "ui-component/cards/ContactCard";

export default function Example() {
  return (
    <ContactCard
    avatar={{}}
    contact={{}}
    email={{}}
    name={{}}
    location={{}}
    onActive={/* TODO */}
    />
  );
}
```
---
## ContactList (`COMP_CONTACTLIST`)
- **File**: `frontend\src\ui-component\cards\ContactList.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `avatar` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ContactList from "ui-component/cards/ContactList";

export default function Example() {
  return (
    <ContactList
    avatar={{}}
    />
  );
}
```
---
## ConversionsChartCard (`COMP_CONVERSIONSCHARTCARD`)
- **File**: `frontend\src\views\widget\Chart\ConversionsChartCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `chartData` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ConversionsChartCard from "views/widget/Chart/ConversionsChartCard";

export default function Example() {
  return (
    <ConversionsChartCard
    chartData={{}}
    />
  );
}
```
---
## CooldownTable (`COMP_COOLDOWNTABLE`)
- **File**: `frontend\src\ui-component\thresholds\CooldownTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CooldownTable from "ui-component/thresholds/CooldownTable";

export default function Example() {
  return (
    <CooldownTable
    />
  );
}
```
---
## CSVExport (`COMP_CSVEXPORT`)
- **File**: `frontend\src\views\forms\tables\TableExports.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `data` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CSVExport from "views/forms/tables/TableExports";

export default function Example() {
  return (
    <CSVExport
    data={{}}
    />
  );
}
```
---
## CustomColumnMenu (`COMP_CUSTOMCOLUMNMENU`)
- **File**: `frontend\src\views\forms\data-grid\ColumnMenu\AddMenuItem.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomColumnMenu from "views/forms/data-grid/ColumnMenu/AddMenuItem";

export default function Example() {
  return (
    <CustomColumnMenu
    />
  );
}
```
---
## CustomComponent (`COMP_CUSTOMCOMPONENT`)
- **File**: `frontend\src\ui-component\extended\notistack\CustomComponent.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomComponent from "ui-component/extended/notistack/CustomComponent";

export default function Example() {
  return (
    <CustomComponent
    />
  );
}
```
---
## CustomDateTime (`COMP_CUSTOMDATETIME`)
- **File**: `frontend\src\views\forms\components\DateTime\CustomDateTime.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomDateTime from "views/forms/components/DateTime/CustomDateTime";

export default function Example() {
  return (
    <CustomDateTime
    />
  );
}
```
---
## CustomEditComponent (`COMP_CUSTOMEDITCOMPONENT`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\CustomEdit.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomEditComponent from "views/forms/data-grid/InLineEditing/CustomEdit";

export default function Example() {
  return (
    <CustomEditComponent
    />
  );
}
```
---
## CustomerSatisfactionCard (`COMP_CUSTOMERSATISFACTIONCARD`)
- **File**: `frontend\src\views\widget\Statistics\CustomerSatisfactionCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomerSatisfactionCard from "views/widget/Statistics/CustomerSatisfactionCard";

export default function Example() {
  return (
    <CustomerSatisfactionCard
    />
  );
}
```
---
## Customization (`COMP_CUSTOMIZATION`)
- **File**: `frontend\src\layout\Customization\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Customization from "layout/Customization/index";

export default function Example() {
  return (
    <Customization
    />
  );
}
```
---
## CustomizationDemo (`COMP_CUSTOMIZATIONDEMO`)
- **File**: `frontend\src\views\forms\data-grid\ColumnGroups\CustomColumnGroup.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `Selected` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomizationDemo from "views/forms/data-grid/ColumnGroups/CustomColumnGroup";

export default function Example() {
  return (
    <CustomizationDemo
    Selected={{}}
    />
  );
}
```
---
## CustomizedTables (`COMP_CUSTOMIZEDTABLES`)
- **File**: `frontend\src\views\forms\tables\TablesCustomized.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomizedTables from "views/forms/tables/TablesCustomized";

export default function Example() {
  return (
    <CustomizedTables
    />
  );
}
```
---
## CustomMenu (`COMP_CUSTOMMENU`)
- **File**: `frontend\src\views\forms\data-grid\ColumnMenu\CustomMenu.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomMenu from "views/forms/data-grid/ColumnMenu/CustomMenu";

export default function Example() {
  return (
    <CustomMenu
    />
  );
}
```
---
## CustomNotistack (`COMP_CUSTOMNOTISTACK`)
- **File**: `frontend\src\ui-component\extended\notistack\CustomComponent.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `id` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomNotistack from "ui-component/extended/notistack/CustomComponent";

export default function Example() {
  return (
    <CustomNotistack
    id={{}}
    />
  );
}
```
---
## CustomShadowBox (`COMP_CUSTOMSHADOWBOX`)
- **File**: `frontend\src\views\utilities\Shadow.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `shadow` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomShadowBox from "views/utilities/Shadow";

export default function Example() {
  return (
    <CustomShadowBox
    shadow="example"
    />
  );
}
```
---
## CustomTabPanel (`COMP_CUSTOMTABPANEL`)
- **File**: `frontend\src\layout\Customization\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomTabPanel from "layout/Customization/index";

export default function Example() {
  return (
    <CustomTabPanel
    children="example"
    />
  );
}
```
---
## CustomUserItem (`COMP_CUSTOMUSERITEM`)
- **File**: `frontend\src\views\forms\data-grid\ColumnMenu\AddMenuItem.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CustomUserItem from "views/forms/data-grid/ColumnMenu/AddMenuItem";

export default function Example() {
  return (
    <CustomUserItem
    />
  );
}
```
---
## CycloneRunSection (`COMP_CYCLONERUNSECTION`)
- **File**: `frontend\src\layout\MainLayout\Header\CycloneRunSection\CycloneRunSection.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import CycloneRunSection from "layout/MainLayout/Header/CycloneRunSection/CycloneRunSection";

export default function Example() {
  return (
    <CycloneRunSection
    />
  );
}
```
---
## Dashboard (`COMP_DASHBOARD`)
- **File**: `frontend\src\views\sonic\index_BU.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Dashboard from "views/sonic/index_BU";

export default function Example() {
  return (
    <Dashboard
    />
  );
}
```
---
## DashboardAnalytics (`COMP_DASHBOARDANALYTICS`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DashboardAnalytics from "routes/MainRoutes";

export default function Example() {
  return (
    <DashboardAnalytics
    />
  );
}
```
---
## DashboardDefault (`COMP_DASHBOARDDEFAULT`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DashboardDefault from "routes/MainRoutes";

export default function Example() {
  return (
    <DashboardDefault
    />
  );
}
```
---
## DashboardGrid (`COMP_DASHBOARDGRID`)
- **File**: `frontend\src\components\dashboard-grid\DashboardGrid.jsx`
- **Used by routes**: `/dashboards/analytics-wire`

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `layout` | `object` | yes | — |
| `wireframe` | `bool` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DashboardGrid from "components/dashboard-grid/DashboardGrid";

export default function Example() {
  return (
    <DashboardGrid
    layout={{}}
    wireframe={false}
    />
  );
}
```
---
## DashboardToggle (`COMP_DASHBOARDTOGGLE`)
- **File**: `frontend\src\components\old\DashboardToggle.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DashboardToggle from "components/old/DashboardToggle";

export default function Example() {
  return (
    <DashboardToggle
    />
  );
}
```
---
## DashRowContainer (`COMP_DASHROWCONTAINER`)
- **File**: `frontend\src\ui-component\containers\DashRowContainer.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DashRowContainer from "ui-component/containers/DashRowContainer";

export default function Example() {
  return (
    <DashRowContainer
    />
  );
}
```
---
## DatabaseViewer (`COMP_DATABASEVIEWER`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DatabaseViewer from "routes/MainRoutes";

export default function Example() {
  return (
    <DatabaseViewer
    />
  );
}
```
---
## DataCard (`COMP_DATACARD`)
- **File**: `frontend\src\views\forms\chart\OrgChart\DataCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `name` | `any` | no | — |
| `role` | `any` | no | — |
| `avatar` | `any` | no | — |
| `linkedin` | `any` | no | — |
| `meet` | `any` | no | — |
| `skype` | `any` | no | — |
| `root` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DataCard from "views/forms/chart/OrgChart/DataCard";

export default function Example() {
  return (
    <DataCard
    name={{}}
    role={{}}
    avatar={{}}
    linkedin={{}}
    meet={{}}
    skype={{}}
    />
  );
}
```
---
## DataGridBasic (`COMP_DATAGRIDBASIC`)
- **File**: `frontend\src\views\forms\data-grid\DataGridBasic\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DataGridBasic from "views/forms/data-grid/DataGridBasic/index";

export default function Example() {
  return (
    <DataGridBasic
    />
  );
}
```
---
## DateTime (`COMP_DATETIME`)
- **File**: `frontend\src\views\forms\components\DateTime\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DateTime from "views/forms/components/DateTime/index";

export default function Example() {
  return (
    <DateTime
    />
  );
}
```
---
## Dense (`COMP_DENSE`)
- **File**: `frontend\src\ui-component\extended\notistack\Dense.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Dense from "ui-component/extended/notistack/Dense";

export default function Example() {
  return (
    <Dense
    />
  );
}
```
---
## DenseTable (`COMP_DENSETABLE`)
- **File**: `frontend\src\views\forms\tables\TableDense.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DenseTable from "views/forms/tables/TableDense";

export default function Example() {
  return (
    <DenseTable
    />
  );
}
```
---
## DisableColumnMenu (`COMP_DISABLECOLUMNMENU`)
- **File**: `frontend\src\views\forms\data-grid\ColumnMenu\DisableMenu.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DisableColumnMenu from "views/forms/data-grid/ColumnMenu/DisableMenu";

export default function Example() {
  return (
    <DisableColumnMenu
    />
  );
}
```
---
## DisableSlider (`COMP_DISABLESLIDER`)
- **File**: `frontend\src\views\forms\components\Slider\DisableSlider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DisableSlider from "views/forms/components/Slider/DisableSlider";

export default function Example() {
  return (
    <DisableSlider
    />
  );
}
```
---
## DisableStopEditModeOnFocusOut (`COMP_DISABLESTOPEDITMODEONFOCUSOUT`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\EditingEvents.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DisableStopEditModeOnFocusOut from "views/forms/data-grid/InLineEditing/EditingEvents";

export default function Example() {
  return (
    <DisableStopEditModeOnFocusOut
    />
  );
}
```
---
## DismissSnackBar (`COMP_DISMISSSNACKBAR`)
- **File**: `frontend\src\ui-component\extended\notistack\DismissSnackBar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DismissSnackBar from "ui-component/extended/notistack/DismissSnackBar";

export default function Example() {
  return (
    <DismissSnackBar
    />
  );
}
```
---
## DonutCountdown (`COMP_DONUTCOUNTDOWN`)
- **File**: `frontend\src\layout\MainLayout\Header\TimerSection\DonutCountdown.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import DonutCountdown from "layout/MainLayout/Header/TimerSection/DonutCountdown";

export default function Example() {
  return (
    <DonutCountdown
    />
  );
}
```
---
## Dropzone (`COMP_DROPZONE`)
- **File**: `frontend\src\views\forms\plugins\Dropzone.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Dropzone from "views/forms/plugins/Dropzone";

export default function Example() {
  return (
    <Dropzone
    />
  );
}
```
---
## EarningCard (`COMP_EARNINGCARD`)
- **File**: `frontend\src\ui-component\cards\Skeleton\EarningCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `isLoading` | `bool` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import EarningCard from "ui-component/cards/Skeleton/EarningCard";

export default function Example() {
  return (
    <EarningCard
    isLoading={false}
    />
  );
}
```
---
## EditableColumn (`COMP_EDITABLECOLUMN`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\EditableColumn.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import EditableColumn from "views/forms/data-grid/InLineEditing/EditableColumn";

export default function Example() {
  return (
    <EditableColumn
    />
  );
}
```
---
## EditColumn (`COMP_EDITCOLUMN`)
- **File**: `frontend\src\views\kanban\Board\EditColumn.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `column` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import EditColumn from "views/kanban/Board/EditColumn";

export default function Example() {
  return (
    <EditColumn
    column={{}}
    />
  );
}
```
---
## EditItem (`COMP_EDITITEM`)
- **File**: `frontend\src\views\kanban\Board\EditItem.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `item` | `any` | no | — |
| `profiles` | `array` | no | — |
| `userStory` | `array` | no | — |
| `columns` | `array` | no | — |
| `handleDrawerOpen` | `func` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import EditItem from "views/kanban/Board/EditItem";

export default function Example() {
  return (
    <EditItem
    item={{}}
    profiles={[]}
    userStory={[]}
    columns={[]}
    handleDrawerOpen={/* TODO */}
    />
  );
}
```
---
## Editor (`COMP_EDITOR`)
- **File**: `frontend\src\views\forms\plugins\Editor.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Editor from "views/forms/plugins/Editor";

export default function Example() {
  return (
    <Editor
    />
  );
}
```
---
## EditStory (`COMP_EDITSTORY`)
- **File**: `frontend\src\views\kanban\Backlogs\EditStory.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `story` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import EditStory from "views/kanban/Backlogs/EditStory";

export default function Example() {
  return (
    <EditStory
    story={{}}
    />
  );
}
```
---
## ElevationScroll (`COMP_ELEVATIONSCROLL`)
- **File**: `frontend\src\layout\MainLayout\HorizontalBar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ElevationScroll from "layout/MainLayout/HorizontalBar";

export default function Example() {
  return (
    <ElevationScroll
    children="example"
    />
  );
}
```
---
## EnhancedTable (`COMP_ENHANCEDTABLE`)
- **File**: `frontend\src\views\forms\tables\TableData.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import EnhancedTable from "views/forms/tables/TableData";

export default function Example() {
  return (
    <EnhancedTable
    />
  );
}
```
---
## EnhancedTableHead (`COMP_ENHANCEDTABLEHEAD`)
- **File**: `frontend\src\views\forms\tables\TableData.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `onSelectAllClick` | `any` | no | — |
| `order` | `any` | no | — |
| `orderBy` | `any` | no | — |
| `numSelected` | `any` | no | — |
| `rowCount` | `any` | no | — |
| `onRequestSort` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import EnhancedTableHead from "views/forms/tables/TableData";

export default function Example() {
  return (
    <EnhancedTableHead
    onSelectAllClick={{}}
    order={{}}
    orderBy={{}}
    numSelected={{}}
    rowCount={{}}
    onRequestSort={{}}
    />
  );
}
```
---
## EnhancedTableToolbar (`COMP_ENHANCEDTABLETOOLBAR`)
- **File**: `frontend\src\views\forms\tables\TableData.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `numSelected` | `number` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import EnhancedTableToolbar from "views/forms/tables/TableData";

export default function Example() {
  return (
    <EnhancedTableToolbar
    numSelected={0}
    />
  );
}
```
---
## Error (`COMP_ERROR`)
- **File**: `frontend\src\views\pages\maintenance\Error.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Error from "views/pages/maintenance/Error";

export default function Example() {
  return (
    <Error
    />
  );
}
```
---
## ErrorBoundary (`COMP_ERRORBOUNDARY`)
- **File**: `frontend\src\routes\ErrorBoundary.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ErrorBoundary from "routes/ErrorBoundary";

export default function Example() {
  return (
    <ErrorBoundary
    />
  );
}
```
---
## ExcludeHiddenColumn (`COMP_EXCLUDEHIDDENCOLUMN`)
- **File**: `frontend\src\views\forms\data-grid\QuickFilter\ExcludeHiddenColumns.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ExcludeHiddenColumn from "views/forms/data-grid/QuickFilter/ExcludeHiddenColumns";

export default function Example() {
  return (
    <ExcludeHiddenColumn
    />
  );
}
```
---
## FeedsCard (`COMP_FEEDSCARD`)
- **File**: `frontend\src\views\widget\Data\FeedsCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FeedsCard from "views/widget/Data/FeedsCard";

export default function Example() {
  return (
    <FeedsCard
    />
  );
}
```
---
## FilesPreview (`COMP_FILESPREVIEW`)
- **File**: `frontend\src\ui-component\third-party\dropzone\FilePreview.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `showList` | `bool` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FilesPreview from "ui-component/third-party/dropzone/FilePreview";

export default function Example() {
  return (
    <FilesPreview
    showList={false}
    />
  );
}
```
---
## FirebaseLogin (`COMP_FIREBASELOGIN`)
- **File**: `frontend\src\views\pages\authentication\firebase\AuthLogin.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FirebaseLogin from "views/pages/authentication/firebase/AuthLogin";

export default function Example() {
  return (
    <FirebaseLogin
    />
  );
}
```
---
## FirebaseProvider (`COMP_FIREBASEPROVIDER`)
- **File**: `frontend\src\contexts\FirebaseContext.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FirebaseProvider from "contexts/FirebaseContext";

export default function Example() {
  return (
    <FirebaseProvider
    children="example"
    />
  );
}
```
---
## FirebaseRegister (`COMP_FIREBASEREGISTER`)
- **File**: `frontend\src\views\pages\authentication\firebase\AuthRegister.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FirebaseRegister from "views/pages/authentication/firebase/AuthRegister";

export default function Example() {
  return (
    <FirebaseRegister
    />
  );
}
```
---
## FirebaseSocial (`COMP_FIREBASESOCIAL`)
- **File**: `frontend\src\views\pages\authentication\firebase\FirebaseSocial.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FirebaseSocial from "views/pages/authentication/firebase/FirebaseSocial";

export default function Example() {
  return (
    <FirebaseSocial
    />
  );
}
```
---
## FloatingCart (`COMP_FLOATINGCART`)
- **File**: `frontend\src\ui-component\cards\FloatingCart.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FloatingCart from "ui-component/cards/FloatingCart";

export default function Example() {
  return (
    <FloatingCart
    />
  );
}
```
---
## FollowerCard (`COMP_FOLLOWERCARD`)
- **File**: `frontend\src\ui-component\cards\FollowerCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `avatar` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FollowerCard from "ui-component/cards/FollowerCard";

export default function Example() {
  return (
    <FollowerCard
    avatar={{}}
    />
  );
}
```
---
## FontFamilyPage (`COMP_FONTFAMILYPAGE`)
- **File**: `frontend\src\layout\Customization\FontFamily.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FontFamilyPage from "layout/Customization/FontFamily";

export default function Example() {
  return (
    <FontFamilyPage
    />
  );
}
```
---
## Footer (`COMP_FOOTER`)
- **File**: `frontend\src\layout\MainLayout\Footer.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Footer from "layout/MainLayout/Footer";

export default function Example() {
  return (
    <Footer
    />
  );
}
```
---
## Forbidden (`COMP_FORBIDDEN`)
- **File**: `frontend\src\views\pages\maintenance\Forbidden.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Forbidden from "views/pages/maintenance/Forbidden";

export default function Example() {
  return (
    <Forbidden
    />
  );
}
```
---
## ForgotPassword (`COMP_FORGOTPASSWORD`)
- **File**: `frontend\src\views\pages\authentication\ForgotPassword.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ForgotPassword from "views/pages/authentication/ForgotPassword";

export default function Example() {
  return (
    <ForgotPassword
    />
  );
}
```
---
## FormControl (`COMP_FORMCONTROL`)
- **File**: `frontend\src\ui-component\extended\Form\FormControl.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `captionLabel` | `string` | no | — |
| `formState` | `string` | no | — |
| `iconPrimary` | `any` | no | — |
| `iconSecondary` | `any` | no | — |
| `placeholder` | `string` | no | — |
| `textPrimary` | `string` | no | — |
| `textSecondary` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FormControl from "ui-component/extended/Form/FormControl";

export default function Example() {
  return (
    <FormControl
    captionLabel="example"
    formState="example"
    iconPrimary={{}}
    iconSecondary={{}}
    placeholder="example"
    textPrimary="example"
    />
  );
}
```
---
## FormControlSelect (`COMP_FORMCONTROLSELECT`)
- **File**: `frontend\src\ui-component\extended\Form\FormControlSelect.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `captionLabel` | `string` | no | — |
| `currencies` | `object` | no | — |
| `formState` | `string` | no | — |
| `iconPrimary` | `any` | no | — |
| `iconSecondary` | `any` | no | — |
| `selected` | `string` | no | — |
| `textPrimary` | `string` | no | — |
| `textSecondary` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FormControlSelect from "ui-component/extended/Form/FormControlSelect";

export default function Example() {
  return (
    <FormControlSelect
    captionLabel="example"
    currencies={{}}
    formState="example"
    iconPrimary={{}}
    iconSecondary={{}}
    selected="example"
    />
  );
}
```
---
## FormRow (`COMP_FORMROW`)
- **File**: `frontend\src\views\utilities\Grid\NestedGrid.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FormRow from "views/utilities/Grid/NestedGrid";

export default function Example() {
  return (
    <FormRow
    />
  );
}
```
---
## FormsValidation (`COMP_FORMSVALIDATION`)
- **File**: `frontend\src\views\forms\forms-validation\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FormsValidation from "views/forms/forms-validation/index";

export default function Example() {
  return (
    <FormsValidation
    />
  );
}
```
---
## FormsWizard (`COMP_FORMSWIZARD`)
- **File**: `frontend\src\views\forms\forms-wizard\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FormsWizard from "views/forms/forms-wizard/index";

export default function Example() {
  return (
    <FormsWizard
    />
  );
}
```
---
## FriendRequestCard (`COMP_FRIENDREQUESTCARD`)
- **File**: `frontend\src\ui-component\cards\FriendRequestCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `avatar` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FriendRequestCard from "ui-component/cards/FriendRequestCard";

export default function Example() {
  return (
    <FriendRequestCard
    avatar={{}}
    />
  );
}
```
---
## FriendsCard (`COMP_FRIENDSCARD`)
- **File**: `frontend\src\ui-component\cards\FriendsCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `avatar` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FriendsCard from "ui-component/cards/FriendsCard";

export default function Example() {
  return (
    <FriendsCard
    avatar={{}}
    />
  );
}
```
---
## FrmAutocomplete (`COMP_FRMAUTOCOMPLETE`)
- **File**: `frontend\src\views\forms\plugins\AutoComplete.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FrmAutocomplete from "views/forms/plugins/AutoComplete";

export default function Example() {
  return (
    <FrmAutocomplete
    />
  );
}
```
---
## FullFeaturedCrudGrid (`COMP_FULLFEATUREDCRUDGRID`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\FullFeatured.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FullFeaturedCrudGrid from "views/forms/data-grid/InLineEditing/FullFeatured";

export default function Example() {
  return (
    <FullFeaturedCrudGrid
    />
  );
}
```
---
## FullScreen (`COMP_FULLSCREEN`)
- **File**: `frontend\src\layout\MainLayout\Header\FullScreenSection\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FullScreen from "layout/MainLayout/Header/FullScreenSection/index";

export default function Example() {
  return (
    <FullScreen
    />
  );
}
```
---
## FullWidthPaper (`COMP_FULLWIDTHPAPER`)
- **File**: `frontend\src\ui-component\cards\FullWidthPaper.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FullWidthPaper from "ui-component/cards/FullWidthPaper";

export default function Example() {
  return (
    <FullWidthPaper
    />
  );
}
```
---
## FunCard (`COMP_FUNCARD`)
- **File**: `frontend\src\ui-component\fun\FunCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import FunCard from "ui-component/fun/FunCard";

export default function Example() {
  return (
    <FunCard
    />
  );
}
```
---
## GalleryCard (`COMP_GALLERYCARD`)
- **File**: `frontend\src\ui-component\cards\GalleryCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `dateTime` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import GalleryCard from "ui-component/cards/GalleryCard";

export default function Example() {
  return (
    <GalleryCard
    dateTime={{}}
    />
  );
}
```
---
## GridSection (`COMP_GRIDSECTION`)
- **File**: `frontend\src\components\dashboard-grid\GridSection.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `section` | `object` | yes | — |
| `wireframe` | `bool` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import GridSection from "components/dashboard-grid/GridSection";

export default function Example() {
  return (
    <GridSection
    section={{}}
    wireframe={false}
    />
  );
}
```
---
## GridSlot (`COMP_GRIDSLOT`)
- **File**: `frontend\src\components\dashboard-grid\GridSlot.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `slotDef` | `object` | yes | — |
| `wireframe` | `bool` | no | — |
| `Widget` | `elementType` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import GridSlot from "components/dashboard-grid/GridSlot";

export default function Example() {
  return (
    <GridSlot
    slotDef={{}}
    wireframe={false}
    Widget={/* TODO */}
    />
  );
}
```
---
## GridSystem (`COMP_GRIDSYSTEM`)
- **File**: `frontend\src\views\utilities\Grid\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import GridSystem from "views/utilities/Grid/index";

export default function Example() {
  return (
    <GridSystem
    />
  );
}
```
---
## GrowTransition (`COMP_GROWTRANSITION`)
- **File**: `frontend\src\ui-component\extended\Snackbar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import GrowTransition from "ui-component/extended/Snackbar";

export default function Example() {
  return (
    <GrowTransition
    />
  );
}
```
---
## GuestGuard (`COMP_GUESTGUARD`)
- **File**: `frontend\src\utils\route-guard\GuestGuard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import GuestGuard from "utils/route-guard/GuestGuard";

export default function Example() {
  return (
    <GuestGuard
    children={{}}
    />
  );
}
```
---
## Header (`COMP_HEADER`)
- **File**: `frontend\src\layout\MainLayout\Header\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Header from "layout/MainLayout/Header/index";

export default function Example() {
  return (
    <Header
    />
  );
}
```
---
## HeaderAvatar (`COMP_HEADERAVATAR`)
- **File**: `frontend\src\layout\MainLayout\Header\MegaMenuSection\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import HeaderAvatar from "layout/MainLayout/Header/MegaMenuSection/index";

export default function Example() {
  return (
    <HeaderAvatar
    children="example"
    />
  );
}
```
---
## HeaderWithIcon (`COMP_HEADERWITHICON`)
- **File**: `frontend\src\views\forms\data-grid\ColumnGroups\CustomColumnGroup.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import HeaderWithIcon from "views/forms/data-grid/ColumnGroups/CustomColumnGroup";

export default function Example() {
  return (
    <HeaderWithIcon
    />
  );
}
```
---
## HedgeEvaluator (`COMP_HEDGEEVALUATOR`)
- **File**: `frontend\src\hedge-report\components\HedgeEvaluator.tsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import HedgeEvaluator from "hedge-report/components/HedgeEvaluator";

export default function Example() {
  return (
    <HedgeEvaluator
    />
  );
}
```
---
## HedgeReportPage (`COMP_HEDGEREPORTPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import HedgeReportPage from "routes/MainRoutes";

export default function Example() {
  return (
    <HedgeReportPage
    />
  );
}
```
---
## HideDuration (`COMP_HIDEDURATION`)
- **File**: `frontend\src\ui-component\extended\notistack\HideDuration.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import HideDuration from "ui-component/extended/notistack/HideDuration";

export default function Example() {
  return (
    <HideDuration
    />
  );
}
```
---
## HideMenuItem (`COMP_HIDEMENUITEM`)
- **File**: `frontend\src\views\forms\data-grid\ColumnMenu\HideMenuItem.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import HideMenuItem from "views/forms/data-grid/ColumnMenu/HideMenuItem";

export default function Example() {
  return (
    <HideMenuItem
    />
  );
}
```
---
## HorizontalBar (`COMP_HORIZONTALBAR`)
- **File**: `frontend\src\layout\MainLayout\HorizontalBar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import HorizontalBar from "layout/MainLayout/HorizontalBar";

export default function Example() {
  return (
    <HorizontalBar
    />
  );
}
```
---
## HoverDataCard (`COMP_HOVERDATACARD`)
- **File**: `frontend\src\ui-component\cards\HoverDataCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `title` | `any` | no | — |
| `iconPrimary` | `object` | no | — |
| `primary` | `any` | no | — |
| `secondary` | `any` | no | — |
| `color` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import HoverDataCard from "ui-component/cards/HoverDataCard";

export default function Example() {
  return (
    <HoverDataCard
    title={{}}
    iconPrimary={{}}
    primary={{}}
    secondary={{}}
    color={{}}
    />
  );
}
```
---
## HoverSocialCard (`COMP_HOVERSOCIALCARD`)
- **File**: `frontend\src\ui-component\cards\HoverSocialCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `primary` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import HoverSocialCard from "ui-component/cards/HoverSocialCard";

export default function Example() {
  return (
    <HoverSocialCard
    primary={{}}
    />
  );
}
```
---
## IconGridCard (`COMP_ICONGRIDCARD`)
- **File**: `frontend\src\views\widget\Statistics\IconGridCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import IconGridCard from "views/widget/Statistics/IconGridCard";

export default function Example() {
  return (
    <IconGridCard
    />
  );
}
```
---
## IconNumberCard (`COMP_ICONNUMBERCARD`)
- **File**: `frontend\src\ui-component\cards\IconNumberCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `title` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import IconNumberCard from "ui-component/cards/IconNumberCard";

export default function Example() {
  return (
    <IconNumberCard
    title={{}}
    />
  );
}
```
---
## IconVariants (`COMP_ICONVARIANTS`)
- **File**: `frontend\src\ui-component\extended\notistack\IconVariants.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import IconVariants from "ui-component/extended/notistack/IconVariants";

export default function Example() {
  return (
    <IconVariants
    />
  );
}
```
---
## IconVariantsContent (`COMP_ICONVARIANTSCONTENT`)
- **File**: `frontend\src\ui-component\extended\notistack\IconVariants.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import IconVariantsContent from "ui-component/extended/notistack/IconVariants";

export default function Example() {
  return (
    <IconVariantsContent
    />
  );
}
```
---
## ImageList (`COMP_IMAGELIST`)
- **File**: `frontend\src\ui-component\extended\ImageList.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `itemData` | `array` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ImageList from "ui-component/extended/ImageList";

export default function Example() {
  return (
    <ImageList
    itemData={[]}
    />
  );
}
```
---
## ImagePlaceholder (`COMP_IMAGEPLACEHOLDER`)
- **File**: `frontend\src\ui-component\cards\Skeleton\ImagePlaceholder.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ImagePlaceholder from "ui-component/cards/Skeleton/ImagePlaceholder";

export default function Example() {
  return (
    <ImagePlaceholder
    />
  );
}
```
---
## IncomingRequests (`COMP_INCOMINGREQUESTS`)
- **File**: `frontend\src\views\widget\Data\IncomingRequests.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import IncomingRequests from "views/widget/Data/IncomingRequests";

export default function Example() {
  return (
    <IncomingRequests
    />
  );
}
```
---
## InitialState (`COMP_INITIALSTATE`)
- **File**: `frontend\src\views\forms\data-grid\SaveRestoreState\InitialState.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import InitialState from "views/forms/data-grid/SaveRestoreState/InitialState";

export default function Example() {
  return (
    <InitialState
    />
  );
}
```
---
## InlineEditing (`COMP_INLINEEDITING`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import InlineEditing from "views/forms/data-grid/InLineEditing/index";

export default function Example() {
  return (
    <InlineEditing
    />
  );
}
```
---
## InputFilled (`COMP_INPUTFILLED`)
- **File**: `frontend\src\layout\Customization\InputFilled.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import InputFilled from "layout/Customization/InputFilled";

export default function Example() {
  return (
    <InputFilled
    />
  );
}
```
---
## InputLabel (`COMP_INPUTLABEL`)
- **File**: `frontend\src\ui-component\extended\Form\InputLabel.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import InputLabel from "ui-component/extended/Form/InputLabel";

export default function Example() {
  return (
    <InputLabel
    children={{}}
    />
  );
}
```
---
## InstantFeedback (`COMP_INSTANTFEEDBACK`)
- **File**: `frontend\src\views\forms\forms-validation\InstantFeedback.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import InstantFeedback from "views/forms/forms-validation/InstantFeedback";

export default function Example() {
  return (
    <InstantFeedback
    />
  );
}
```
---
## IsCellEditableGrid (`COMP_ISCELLEDITABLEGRID`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\DisableEditing.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import IsCellEditableGrid from "views/forms/data-grid/InLineEditing/DisableEditing";

export default function Example() {
  return (
    <IsCellEditableGrid
    />
  );
}
```
---
## Item (`COMP_ITEM`)
- **File**: `frontend\src\views\pages\maintenance\ComingSoon\ComingSoon1\Slider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `item` | `object` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Item from "views/pages/maintenance/ComingSoon/ComingSoon1/Slider";

export default function Example() {
  return (
    <Item
    item={{}}
    />
  );
}
```
---
## ItemComment (`COMP_ITEMCOMMENT`)
- **File**: `frontend\src\views\kanban\Board\ItemComment.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `comment` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ItemComment from "views/kanban/Board/ItemComment";

export default function Example() {
  return (
    <ItemComment
    comment={{}}
    />
  );
}
```
---
## ItemDetails (`COMP_ITEMDETAILS`)
- **File**: `frontend\src\views\kanban\Board\ItemDetails.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ItemDetails from "views/kanban/Board/ItemDetails";

export default function Example() {
  return (
    <ItemDetails
    />
  );
}
```
---
## Items (`COMP_ITEMS`)
- **File**: `frontend\src\views\kanban\Backlogs\Items.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `item` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Items from "views/kanban/Backlogs/Items";

export default function Example() {
  return (
    <Items
    item={{}}
    />
  );
}
```
---
## JupiterPage (`COMP_JUPITERPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import JupiterPage from "routes/MainRoutes";

export default function Example() {
  return (
    <JupiterPage
    />
  );
}
```
---
## JWTLogin (`COMP_JWTLOGIN`)
- **File**: `frontend\src\views\pages\authentication\jwt\AuthLogin.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import JWTLogin from "views/pages/authentication/jwt/AuthLogin";

export default function Example() {
  return (
    <JWTLogin
    />
  );
}
```
---
## JWTProvider (`COMP_JWTPROVIDER`)
- **File**: `frontend\src\contexts\JWTContext.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import JWTProvider from "contexts/JWTContext";

export default function Example() {
  return (
    <JWTProvider
    children="example"
    />
  );
}
```
---
## JWTRegister (`COMP_JWTREGISTER`)
- **File**: `frontend\src\views\pages\authentication\jwt\AuthRegister.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import JWTRegister from "views/pages/authentication/jwt/AuthRegister";

export default function Example() {
  return (
    <JWTRegister
    />
  );
}
```
---
## KanbanBacklogs (`COMP_KANBANBACKLOGS`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import KanbanBacklogs from "routes/MainRoutes";

export default function Example() {
  return (
    <KanbanBacklogs
    />
  );
}
```
---
## KanbanBoard (`COMP_KANBANBOARD`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import KanbanBoard from "routes/MainRoutes";

export default function Example() {
  return (
    <KanbanBoard
    />
  );
}
```
---
## KanbanPage (`COMP_KANBANPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import KanbanPage from "routes/MainRoutes";

export default function Example() {
  return (
    <KanbanPage
    />
  );
}
```
---
## LabelSlider (`COMP_LABELSLIDER`)
- **File**: `frontend\src\views\forms\components\Slider\LabelSlider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LabelSlider from "views/forms/components/Slider/LabelSlider";

export default function Example() {
  return (
    <LabelSlider
    />
  );
}
```
---
## LandscapeDateTime (`COMP_LANDSCAPEDATETIME`)
- **File**: `frontend\src\views\forms\components\DateTime\LandscapeDateTime.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LandscapeDateTime from "views/forms/components/DateTime/LandscapeDateTime";

export default function Example() {
  return (
    <LandscapeDateTime
    />
  );
}
```
---
## LatestCustomers (`COMP_LATESTCUSTOMERS`)
- **File**: `frontend\src\views\widget\Data\LatestCustomers.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LatestCustomers from "views/widget/Data/LatestCustomers";

export default function Example() {
  return (
    <LatestCustomers
    />
  );
}
```
---
## LatestMessages (`COMP_LATESTMESSAGES`)
- **File**: `frontend\src\views\widget\Data\LatestMessages.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LatestMessages from "views/widget/Data/LatestMessages";

export default function Example() {
  return (
    <LatestMessages
    />
  );
}
```
---
## LatestOrder (`COMP_LATESTORDER`)
- **File**: `frontend\src\views\widget\Data\LatestOrder.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LatestOrder from "views/widget/Data/LatestOrder";

export default function Example() {
  return (
    <LatestOrder
    />
  );
}
```
---
## LatestPosts (`COMP_LATESTPOSTS`)
- **File**: `frontend\src\views\widget\Data\LatestPosts.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LatestPosts from "views/widget/Data/LatestPosts";

export default function Example() {
  return (
    <LatestPosts
    />
  );
}
```
---
## Layout (`COMP_LAYOUT`)
- **File**: `frontend\src\layout\Customization\Layout.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Layout from "layout/Customization/Layout";

export default function Example() {
  return (
    <Layout
    />
  );
}
```
---
## Layouts (`COMP_LAYOUTS`)
- **File**: `frontend\src\views\forms\layouts\Layouts.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Layouts from "views/forms/layouts/Layouts";

export default function Example() {
  return (
    <Layouts
    />
  );
}
```
---
## LinearProgressWithLabel (`COMP_LINEARPROGRESSWITHLABEL`)
- **File**: `frontend\src\layout\MainLayout\Sidebar\MenuCard\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `value` | `number` | yes | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LinearProgressWithLabel from "layout/MainLayout/Sidebar/MenuCard/index";

export default function Example() {
  return (
    <LinearProgressWithLabel
    value={0}
    />
  );
}
```
---
## LinkedIn (`COMP_LINKEDIN`)
- **File**: `frontend\src\views\forms\chart\OrgChart\LinkedIn.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LinkedIn from "views/forms/chart/OrgChart/LinkedIn";

export default function Example() {
  return (
    <LinkedIn
    />
  );
}
```
---
## LiqRow (`COMP_LIQROW`)
- **File**: `frontend\src\ui-component\liquidation\LiqRow.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LiqRow from "ui-component/liquidation/LiqRow";

export default function Example() {
  return (
    <LiqRow
    />
  );
}
```
---
## LiquidationBars (`COMP_LIQUIDATIONBARS`)
- **File**: `frontend\src\ui-component\liquidation\LiquidationBars.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LiquidationBars from "ui-component/liquidation/LiquidationBars";

export default function Example() {
  return (
    <LiquidationBars
    />
  );
}
```
---
## LiquidationBarsCard (`COMP_LIQUIDATIONBARSCARD`)
- **File**: `frontend\src\views\positions\LiquidationBarsCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LiquidationBarsCard from "views/positions/LiquidationBarsCard";

export default function Example() {
  return (
    <LiquidationBarsCard
    />
  );
}
```
---
## LiquidationDistanceIcon (`COMP_LIQUIDATIONDISTANCEICON`)
- **File**: `frontend\src\views\alertThresholds\icons.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LiquidationDistanceIcon from "views/alertThresholds/icons";

export default function Example() {
  return (
    <LiquidationDistanceIcon
    />
  );
}
```
---
## LiquidationMonitorCard (`COMP_LIQUIDATIONMONITORCARD`)
- **File**: `frontend\src\views\monitorManager\LiquidationMonitorCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LiquidationMonitorCard from "views/monitorManager/LiquidationMonitorCard";

export default function Example() {
  return (
    <LiquidationMonitorCard
    />
  );
}
```
---
## ListItemWrapper (`COMP_LISTITEMWRAPPER`)
- **File**: `frontend\src\layout\MainLayout\Header\NotificationSection\NotificationList.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ListItemWrapper from "layout/MainLayout/Header/NotificationSection/NotificationList";

export default function Example() {
  return (
    <ListItemWrapper
    />
  );
}
```
---
## Loadable (`COMP_LOADABLE`)
- **File**: `frontend\src\ui-component\Loadable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Loadable from "ui-component/Loadable";

export default function Example() {
  return (
    <Loadable
    />
  );
}
```
---
## Loader (`COMP_LOADER`)
- **File**: `frontend\src\ui-component\Loader.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Loader from "ui-component/Loader";

export default function Example() {
  return (
    <Loader
    />
  );
}
```
---
## Locales (`COMP_LOCALES`)
- **File**: `frontend\src\ui-component\Locales.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Locales from "ui-component/Locales";

export default function Example() {
  return (
    <Locales
    children="example"
    />
  );
}
```
---
## LocalizationSection (`COMP_LOCALIZATIONSECTION`)
- **File**: `frontend\src\layout\MainLayout\Header\LocalizationSection\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LocalizationSection from "layout/MainLayout/Header/LocalizationSection/index";

export default function Example() {
  return (
    <LocalizationSection
    />
  );
}
```
---
## LogConsole (`COMP_LOGCONSOLE`)
- **File**: `frontend\src\views\sonicLabs\SonicLabsPage.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LogConsole from "views/sonicLabs/SonicLabsPage";

export default function Example() {
  return (
    <LogConsole
    />
  );
}
```
---
## Login (`COMP_LOGIN`)
- **File**: `frontend\src\views\pages\authentication\Login.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Login from "views/pages/authentication/Login";

export default function Example() {
  return (
    <Login
    />
  );
}
```
---
## LoginForms (`COMP_LOGINFORMS`)
- **File**: `frontend\src\views\forms\forms-validation\LoginForms.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LoginForms from "views/forms/forms-validation/LoginForms";

export default function Example() {
  return (
    <LoginForms
    />
  );
}
```
---
## LoginProvider (`COMP_LOGINPROVIDER`)
- **File**: `frontend\src\views\pages\authentication\LoginProvider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `currentLoginWith` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LoginProvider from "views/pages/authentication/LoginProvider";

export default function Example() {
  return (
    <LoginProvider
    currentLoginWith="example"
    />
  );
}
```
---
## Logo (`COMP_LOGO`)
- **File**: `frontend\src\ui-component\Logo.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Logo from "ui-component/Logo";

export default function Example() {
  return (
    <Logo
    />
  );
}
```
---
## LogoSection (`COMP_LOGOSECTION`)
- **File**: `frontend\src\layout\MainLayout\LogoSection\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LogoSection from "layout/MainLayout/LogoSection/index";

export default function Example() {
  return (
    <LogoSection
    />
  );
}
```
---
## LS_KEY (`COMP_LS_KEY`)
- **File**: `frontend\src\theme\tokens.js`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import LS_KEY from "theme/tokens";

export default function Example() {
  return (
    <LS_KEY
    />
  );
}
```
---
## MailerSubscriber (`COMP_MAILERSUBSCRIBER`)
- **File**: `frontend\src\views\pages\maintenance\ComingSoon\ComingSoon1\MailerSubscriber.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MailerSubscriber from "views/pages/maintenance/ComingSoon/ComingSoon1/MailerSubscriber";

export default function Example() {
  return (
    <MailerSubscriber
    />
  );
}
```
---
## MainCard (`COMP_MAINCARD`)
- **File**: `frontend\src\ui-component\cards\MainCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `border` | `bool` | no | — |
| `boxShadow` | `bool` | no | — |
| `children` | `oneOfType` | no | — |
| `content` | `bool` | no | — |
| `contentClass` | `string` | no | — |
| `contentSX` | `object` | no | — |
| `headerSX` | `object` | no | — |
| `darkTitle` | `bool` | no | — |
| `secondary` | `any` | no | — |
| `shadow` | `string` | no | — |
| `sx` | `object` | no | — |
| `title` | `oneOfType` | no | — |
| `ref` | `object` | no | — |
| `others` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MainCard from "ui-component/cards/MainCard";

export default function Example() {
  return (
    <MainCard
    border={false}
    boxShadow={false}
    children={/* TODO */}
    content={false}
    contentClass="example"
    contentSX={{}}
    />
  );
}
```
---
## MainLayout (`COMP_MAINLAYOUT`)
- **File**: `frontend\src\layout\MainLayout\index.jsx`
- **Used by routes**: `/`, `/trader-shop`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MainLayout from "layout/MainLayout/index";

export default function Example() {
  return (
    <MainLayout
    />
  );
}
```
---
## MaintenanceComingSoon1 (`COMP_MAINTENANCECOMINGSOON1`)
- **File**: `frontend\src\routes\AuthenticationRoutes.jsx`
- **Used by routes**: `/forbidden`, `/pages/500`, `/pages/coming-soon1`, `/pages/coming-soon2`, `/pages/error`, `/pages/under-construction`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MaintenanceComingSoon1 from "routes/AuthenticationRoutes";

export default function Example() {
  return (
    <MaintenanceComingSoon1
    />
  );
}
```
---
## MaintenanceComingSoon2 (`COMP_MAINTENANCECOMINGSOON2`)
- **File**: `frontend\src\routes\AuthenticationRoutes.jsx`
- **Used by routes**: `/forbidden`, `/pages/500`, `/pages/coming-soon1`, `/pages/coming-soon2`, `/pages/error`, `/pages/under-construction`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MaintenanceComingSoon2 from "routes/AuthenticationRoutes";

export default function Example() {
  return (
    <MaintenanceComingSoon2
    />
  );
}
```
---
## MaintenanceError (`COMP_MAINTENANCEERROR`)
- **File**: `frontend\src\routes\AuthenticationRoutes.jsx`
- **Used by routes**: `/forbidden`, `/pages/500`, `/pages/coming-soon1`, `/pages/coming-soon2`, `/pages/error`, `/pages/under-construction`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MaintenanceError from "routes/AuthenticationRoutes";

export default function Example() {
  return (
    <MaintenanceError
    />
  );
}
```
---
## MaintenanceError500 (`COMP_MAINTENANCEERROR500`)
- **File**: `frontend\src\routes\AuthenticationRoutes.jsx`
- **Used by routes**: `/forbidden`, `/pages/500`, `/pages/coming-soon1`, `/pages/coming-soon2`, `/pages/error`, `/pages/under-construction`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MaintenanceError500 from "routes/AuthenticationRoutes";

export default function Example() {
  return (
    <MaintenanceError500
    />
  );
}
```
---
## MaintenanceForbidden (`COMP_MAINTENANCEFORBIDDEN`)
- **File**: `frontend\src\routes\AuthenticationRoutes.jsx`
- **Used by routes**: `/forbidden`, `/pages/500`, `/pages/coming-soon1`, `/pages/coming-soon2`, `/pages/error`, `/pages/under-construction`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MaintenanceForbidden from "routes/AuthenticationRoutes";

export default function Example() {
  return (
    <MaintenanceForbidden
    />
  );
}
```
---
## MaintenanceUnderConstruction (`COMP_MAINTENANCEUNDERCONSTRUCTION`)
- **File**: `frontend\src\routes\AuthenticationRoutes.jsx`
- **Used by routes**: `/forbidden`, `/pages/500`, `/pages/coming-soon1`, `/pages/coming-soon2`, `/pages/error`, `/pages/under-construction`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MaintenanceUnderConstruction from "routes/AuthenticationRoutes";

export default function Example() {
  return (
    <MaintenanceUnderConstruction
    />
  );
}
```
---
## MarketChartCard (`COMP_MARKETCHARTCARD`)
- **File**: `frontend\src\views\widget\Chart\MarketSaleChartCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `chartData` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MarketChartCard from "views/widget/Chart/MarketSaleChartCard";

export default function Example() {
  return (
    <MarketChartCard
    chartData={{}}
    />
  );
}
```
---
## MarketMonitorCard (`COMP_MARKETMONITORCARD`)
- **File**: `frontend\src\views\monitorManager\MarketMonitorCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MarketMonitorCard from "views/monitorManager/MarketMonitorCard";

export default function Example() {
  return (
    <MarketMonitorCard
    />
  );
}
```
---
## MarketMovementCard (`COMP_MARKETMOVEMENTCARD`)
- **File**: `frontend\src\components\MarketMovementCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MarketMovementCard from "components/MarketMovementCard";

export default function Example() {
  return (
    <MarketMovementCard
    />
  );
}
```
---
## MarketsPanel (`COMP_MARKETSPANEL`)
- **File**: `frontend\src\components\jupiter\Perps\MarketsPanel.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MarketsPanel from "components/jupiter/Perps/MarketsPanel";

export default function Example() {
  return (
    <MarketsPanel
    />
  );
}
```
---
## MaskPage (`COMP_MASKPAGE`)
- **File**: `frontend\src\views\forms\plugins\Mask.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MaskPage from "views/forms/plugins/Mask";

export default function Example() {
  return (
    <MaskPage
    />
  );
}
```
---
## MaxSnackbar (`COMP_MAXSNACKBAR`)
- **File**: `frontend\src\ui-component\extended\notistack\MaxSnackbar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MaxSnackbar from "ui-component/extended/notistack/MaxSnackbar";

export default function Example() {
  return (
    <MaxSnackbar
    />
  );
}
```
---
## MeetIcon (`COMP_MEETICON`)
- **File**: `frontend\src\views\forms\chart\OrgChart\MeetIcon.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MeetIcon from "views/forms/chart/OrgChart/MeetIcon";

export default function Example() {
  return (
    <MeetIcon
    />
  );
}
```
---
## MegaMenuBanner (`COMP_MEGAMENUBANNER`)
- **File**: `frontend\src\layout\MainLayout\Header\MegaMenuSection\Banner.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MegaMenuBanner from "layout/MainLayout/Header/MegaMenuSection/Banner";

export default function Example() {
  return (
    <MegaMenuBanner
    />
  );
}
```
---
## MegaMenuSection (`COMP_MEGAMENUSECTION`)
- **File**: `frontend\src\layout\MainLayout\Header\MegaMenuSection\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MegaMenuSection from "layout/MainLayout/Header/MegaMenuSection/index";

export default function Example() {
  return (
    <MegaMenuSection
    />
  );
}
```
---
## MenuCard (`COMP_MENUCARD`)
- **File**: `frontend\src\layout\MainLayout\Sidebar\MenuCard\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MenuCard from "layout/MainLayout/Sidebar/MenuCard/index";

export default function Example() {
  return (
    <MenuCard
    />
  );
}
```
---
## MenuCloseComponent (`COMP_MENUCLOSECOMPONENT`)
- **File**: `frontend\src\views\forms\data-grid\ColumnMenu\CustomMenu.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MenuCloseComponent from "views/forms/data-grid/ColumnMenu/CustomMenu";

export default function Example() {
  return (
    <MenuCloseComponent
    />
  );
}
```
---
## MenuList (`COMP_MENULIST`)
- **File**: `frontend\src\layout\MainLayout\MenuList\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MenuList from "layout/MainLayout/MenuList/index";

export default function Example() {
  return (
    <MenuList
    />
  );
}
```
---
## MenuOrientationPage (`COMP_MENUORIENTATIONPAGE`)
- **File**: `frontend\src\layout\Customization\MenuOrientation.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MenuOrientationPage from "layout/Customization/MenuOrientation";

export default function Example() {
  return (
    <MenuOrientationPage
    />
  );
}
```
---
## MinimalLayout (`COMP_MINIMALLAYOUT`)
- **File**: `frontend\src\layout\MinimalLayout\index.jsx`
- **Used by routes**: `/`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MinimalLayout from "layout/MinimalLayout/index";

export default function Example() {
  return (
    <MinimalLayout
    />
  );
}
```
---
## MobileSearch (`COMP_MOBILESEARCH`)
- **File**: `frontend\src\layout\MainLayout\Header\SearchSection\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `value` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MobileSearch from "layout/MainLayout/Header/SearchSection/index";

export default function Example() {
  return (
    <MobileSearch
    value="example"
    />
  );
}
```
---
## MobileSection (`COMP_MOBILESECTION`)
- **File**: `frontend\src\layout\MainLayout\Header\MobileSection\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MobileSection from "layout/MainLayout/Header/MobileSection/index";

export default function Example() {
  return (
    <MobileSection
    />
  );
}
```
---
## Modal (`COMP_MODAL`)
- **File**: `frontend\src\views\forms\plugins\Modal\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Modal from "views/forms/plugins/Modal/index";

export default function Example() {
  return (
    <Modal
    />
  );
}
```
---
## MonitorManager (`COMP_MONITORMANAGER`)
- **File**: `frontend\src\views\monitorManager\MonitorManager.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MonitorManager from "views/monitorManager/MonitorManager";

export default function Example() {
  return (
    <MonitorManager
    />
  );
}
```
---
## MonitorManagerPage (`COMP_MONITORMANAGERPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MonitorManagerPage from "routes/MainRoutes";

export default function Example() {
  return (
    <MonitorManagerPage
    />
  );
}
```
---
## MonitorUpdateBar (`COMP_MONITORUPDATEBAR`)
- **File**: `frontend\src\views\monitorManager\MonitorUpdateBar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MonitorUpdateBar from "views/monitorManager/MonitorUpdateBar";

export default function Example() {
  return (
    <MonitorUpdateBar
    />
  );
}
```
---
## MultiFileUpload (`COMP_MULTIFILEUPLOAD`)
- **File**: `frontend\src\ui-component\third-party\dropzone\MultiFile.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `error` | `any` | no | — |
| `showList` | `bool` | no | — |
| `files` | `any` | no | — |
| `type` | `any` | no | — |
| `setFieldValue` | `any` | no | — |
| `sx` | `any` | no | — |
| `onUpload` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MultiFileUpload from "ui-component/third-party/dropzone/MultiFile";

export default function Example() {
  return (
    <MultiFileUpload
    error={{}}
    showList={false}
    files={{}}
    type={{}}
    setFieldValue={{}}
    sx={{}}
    />
  );
}
```
---
## MultipleBreakPoints (`COMP_MULTIPLEBREAKPOINTS`)
- **File**: `frontend\src\views\utilities\Grid\MultipleBreakPoints.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import MultipleBreakPoints from "views/utilities/Grid/MultipleBreakPoints";

export default function Example() {
  return (
    <MultipleBreakPoints
    />
  );
}
```
---
## NameEditInputCell (`COMP_NAMEEDITINPUTCELL`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\Validation.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import NameEditInputCell from "views/forms/data-grid/InLineEditing/Validation";

export default function Example() {
  return (
    <NameEditInputCell
    />
  );
}
```
---
## NavCollapse (`COMP_NAVCOLLAPSE`)
- **File**: `frontend\src\layout\MainLayout\MenuList\NavCollapse\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `menu` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import NavCollapse from "layout/MainLayout/MenuList/NavCollapse/index";

export default function Example() {
  return (
    <NavCollapse
    menu={{}}
    />
  );
}
```
---
## NavGroup (`COMP_NAVGROUP`)
- **File**: `frontend\src\layout\MainLayout\MenuList\NavGroup\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `item` | `any` | no | — |
| `lastItem` | `number` | no | — |
| `remItems` | `array` | no | — |
| `lastItemId` | `string` | no | — |
| `selectedID` | `oneOfType` | no | — |
| `setSelectedID` | `oneOfType` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import NavGroup from "layout/MainLayout/MenuList/NavGroup/index";

export default function Example() {
  return (
    <NavGroup
    item={{}}
    lastItem={0}
    remItems={[]}
    lastItemId="example"
    selectedID={/* TODO */}
    setSelectedID={/* TODO */}
    />
  );
}
```
---
## NavigationScroll (`COMP_NAVIGATIONSCROLL`)
- **File**: `frontend\src\layout\NavigationScroll.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `oneOfType` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import NavigationScroll from "layout/NavigationScroll";

export default function Example() {
  return (
    <NavigationScroll
    children={/* TODO */}
    />
  );
}
```
---
## NavItem (`COMP_NAVITEM`)
- **File**: `frontend\src\layout\MainLayout\MenuList\NavItem\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `item` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import NavItem from "layout/MainLayout/MenuList/NavItem/index";

export default function Example() {
  return (
    <NavItem
    item={{}}
    />
  );
}
```
---
## NavMotion (`COMP_NAVMOTION`)
- **File**: `frontend\src\layout\NavMotion.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import NavMotion from "layout/NavMotion";

export default function Example() {
  return (
    <NavMotion
    children="example"
    />
  );
}
```
---
## NestedGrid (`COMP_NESTEDGRID`)
- **File**: `frontend\src\views\utilities\Grid\NestedGrid.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import NestedGrid from "views/utilities/Grid/NestedGrid";

export default function Example() {
  return (
    <NestedGrid
    />
  );
}
```
---
## NewCustomers (`COMP_NEWCUSTOMERS`)
- **File**: `frontend\src\views\widget\Data\NewCustomers.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import NewCustomers from "views/widget/Data/NewCustomers";

export default function Example() {
  return (
    <NewCustomers
    />
  );
}
```
---
## NotificationList (`COMP_NOTIFICATIONLIST`)
- **File**: `frontend\src\layout\MainLayout\Header\NotificationSection\NotificationList.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `items` | `array` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import NotificationList from "layout/MainLayout/Header/NotificationSection/NotificationList";

export default function Example() {
  return (
    <NotificationList
    items={[]}
    />
  );
}
```
---
## NotificationSection (`COMP_NOTIFICATIONSECTION`)
- **File**: `frontend\src\layout\MainLayout\Header\NotificationSection\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import NotificationSection from "layout/MainLayout/Header/NotificationSection/index";

export default function Example() {
  return (
    <NotificationSection
    />
  );
}
```
---
## Notistack (`COMP_NOTISTACK`)
- **File**: `frontend\src\ui-component\third-party\Notistack.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Notistack from "ui-component/third-party/Notistack";

export default function Example() {
  return (
    <Notistack
    children={{}}
    />
  );
}
```
---
## OperationsBar (`COMP_OPERATIONSBAR`)
- **File**: `frontend\src\components\old\OperationsBar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import OperationsBar from "components/old/OperationsBar";

export default function Example() {
  return (
    <OperationsBar
    />
  );
}
```
---
## OrderForm (`COMP_ORDERFORM`)
- **File**: `frontend\src\components\jupiter\Perps\OrderForm.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import OrderForm from "components/jupiter/Perps/OrderForm";

export default function Example() {
  return (
    <OrderForm
    />
  );
}
```
---
## OrgChartPage (`COMP_ORGCHARTPAGE`)
- **File**: `frontend\src\views\forms\chart\OrgChart\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import OrgChartPage from "views/forms/chart/OrgChart/index";

export default function Example() {
  return (
    <OrgChartPage
    />
  );
}
```
---
## OverrideMenu (`COMP_OVERRIDEMENU`)
- **File**: `frontend\src\views\forms\data-grid\ColumnMenu\OverrideMenu.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import OverrideMenu from "views/forms/data-grid/ColumnMenu/OverrideMenu";

export default function Example() {
  return (
    <OverrideMenu
    />
  );
}
```
---
## OverviewPage (`COMP_OVERVIEWPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import OverviewPage from "routes/MainRoutes";

export default function Example() {
  return (
    <OverviewPage
    />
  );
}
```
---
## Palette (`COMP_PALETTE`)
- **File**: `frontend\src\themes\palette.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Palette from "themes/palette";

export default function Example() {
  return (
    <Palette
    />
  );
}
```
---
## ParsingValues (`COMP_PARSINGVALUES`)
- **File**: `frontend\src\views\forms\data-grid\QuickFilter\ParsingValues.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ParsingValues from "views/forms/data-grid/QuickFilter/ParsingValues";

export default function Example() {
  return (
    <ParsingValues
    />
  );
}
```
---
## PaymentForm (`COMP_PAYMENTFORM`)
- **File**: `frontend\src\views\forms\forms-wizard\BasicWizard\PaymentForm.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `paymentData` | `any` | no | — |
| `setPaymentData` | `func` | no | — |
| `handleNext` | `func` | no | — |
| `handleBack` | `func` | no | — |
| `setErrorIndex` | `func` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PaymentForm from "views/forms/forms-wizard/BasicWizard/PaymentForm";

export default function Example() {
  return (
    <PaymentForm
    paymentData={{}}
    setPaymentData={/* TODO */}
    handleNext={/* TODO */}
    handleBack={/* TODO */}
    setErrorIndex={/* TODO */}
    />
  );
}
```
---
## PerfChip (`COMP_PERFCHIP`)
- **File**: `frontend\src\components\PerformanceGraphCard\PerformanceGraphCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PerfChip from "components/PerformanceGraphCard/PerformanceGraphCard";

export default function Example() {
  return (
    <PerfChip
    />
  );
}
```
---
## PerformanceGraphCard (`COMP_PERFORMANCEGRAPHCARD`)
- **File**: `frontend\src\components\PerformanceGraphCard\PerformanceGraphCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PerformanceGraphCard from "components/PerformanceGraphCard/PerformanceGraphCard";

export default function Example() {
  return (
    <PerformanceGraphCard
    />
  );
}
```
---
## PlaceholderContent (`COMP_PLACEHOLDERCONTENT`)
- **File**: `frontend\src\ui-component\third-party\dropzone\PlaceHolderContent.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `type` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PlaceholderContent from "ui-component/third-party/dropzone/PlaceHolderContent";

export default function Example() {
  return (
    <PlaceholderContent
    type="example"
    />
  );
}
```
---
## PopularCard (`COMP_POPULARCARD`)
- **File**: `frontend\src\ui-component\cards\Skeleton\PopularCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `isLoading` | `bool` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PopularCard from "ui-component/cards/Skeleton/PopularCard";

export default function Example() {
  return (
    <PopularCard
    isLoading={false}
    />
  );
}
```
---
## PopupSlider (`COMP_POPUPSLIDER`)
- **File**: `frontend\src\views\forms\components\Slider\PopupSlider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PopupSlider from "views/forms/components/Slider/PopupSlider";

export default function Example() {
  return (
    <PopupSlider
    />
  );
}
```
---
## PortfolioBar (`COMP_PORTFOLIOBAR`)
- **File**: `frontend\src\components\old\PortfolioBar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PortfolioBar from "components/old/PortfolioBar";

export default function Example() {
  return (
    <PortfolioBar
    />
  );
}
```
---
## PortfolioSessionCard (`COMP_PORTFOLIOSESSIONCARD`)
- **File**: `frontend\src\components\PortfolioSessionCard\PortfolioSessionCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `snapshot` | `object` | no | — |
| `currentValueUsd` | `number` | no | — |
| `onModify` | `func` | no | — |
| `onReset` | `func` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PortfolioSessionCard from "components/PortfolioSessionCard/PortfolioSessionCard";

export default function Example() {
  return (
    <PortfolioSessionCard
    snapshot={{}}
    currentValueUsd={0}
    onModify={/* TODO */}
    onReset={/* TODO */}
    />
  );
}
```
---
## PositioningSnackbar (`COMP_POSITIONINGSNACKBAR`)
- **File**: `frontend\src\ui-component\extended\notistack\PositioningSnackbar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PositioningSnackbar from "ui-component/extended/notistack/PositioningSnackbar";

export default function Example() {
  return (
    <PositioningSnackbar
    />
  );
}
```
---
## PositionListCard (`COMP_POSITIONLISTCARD`)
- **File**: `frontend\src\components\PositionListCard\PositionListCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `title` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PositionListCard from "components/PositionListCard/PositionListCard";

export default function Example() {
  return (
    <PositionListCard
    title="example"
    />
  );
}
```
---
## PositionPieCard (`COMP_POSITIONPIECARD`)
- **File**: `frontend\src\components\PositionPieCard\PositionPieCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `maxHeight` | `oneOfType` | no | — |
| `maxWidth` | `oneOfType` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PositionPieCard from "components/PositionPieCard/PositionPieCard";

export default function Example() {
  return (
    <PositionPieCard
    maxHeight={/* TODO */}
    maxWidth={/* TODO */}
    />
  );
}
```
---
## PositionsCell (`COMP_POSITIONSCELL`)
- **File**: `frontend\src\ui-component\wallet\WalletTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PositionsCell from "ui-component/wallet/WalletTable";

export default function Example() {
  return (
    <PositionsCell
    />
  );
}
```
---
## PositionsPage (`COMP_POSITIONSPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PositionsPage from "routes/MainRoutes";

export default function Example() {
  return (
    <PositionsPage
    />
  );
}
```
---
## PositionsPanel (`COMP_POSITIONSPANEL`)
- **File**: `frontend\src\components\jupiter\Perps\PositionsPanel.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PositionsPanel from "components/jupiter/Perps/PositionsPanel";

export default function Example() {
  return (
    <PositionsPanel
    />
  );
}
```
---
## PositionsTable (`COMP_POSITIONSTABLE`)
- **File**: `frontend\src\hedge-report\components\PositionsTable.tsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PositionsTable from "hedge-report/components/PositionsTable";

export default function Example() {
  return (
    <PositionsTable
    />
  );
}
```
---
## PositionsTableCard (`COMP_POSITIONSTABLECARD`)
- **File**: `frontend\src\ui-component\cards\positions\PositionsTableCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PositionsTableCard from "ui-component/cards/positions/PositionsTableCard";

export default function Example() {
  return (
    <PositionsTableCard
    />
  );
}
```
---
## PositionTableCard (`COMP_POSITIONTABLECARD`)
- **File**: `frontend\src\views\positions\PositionTableCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PositionTableCard from "views/positions/PositionTableCard";

export default function Example() {
  return (
    <PositionTableCard
    />
  );
}
```
---
## PresetColorBox (`COMP_PRESETCOLORBOX`)
- **File**: `frontend\src\layout\Customization\PresetColor.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `color` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PresetColorBox from "layout/Customization/PresetColor";

export default function Example() {
  return (
    <PresetColorBox
    color={{}}
    />
  );
}
```
---
## PresetColorPage (`COMP_PRESETCOLORPAGE`)
- **File**: `frontend\src\layout\Customization\PresetColor.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PresetColorPage from "layout/Customization/PresetColor";

export default function Example() {
  return (
    <PresetColorPage
    />
  );
}
```
---
## PreventDuplicate (`COMP_PREVENTDUPLICATE`)
- **File**: `frontend\src\ui-component\extended\notistack\PreventDuplicate.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import PreventDuplicate from "ui-component/extended/notistack/PreventDuplicate";

export default function Example() {
  return (
    <PreventDuplicate
    />
  );
}
```
---
## ProductCard (`COMP_PRODUCTCARD`)
- **File**: `frontend\src\ui-component\cards\ProductCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `id` | `any` | no | — |
| `color` | `any` | no | — |
| `name` | `any` | no | — |
| `image` | `any` | no | — |
| `description` | `any` | no | — |
| `offerPrice` | `any` | no | — |
| `salePrice` | `any` | no | — |
| `rating` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ProductCard from "ui-component/cards/ProductCard";

export default function Example() {
  return (
    <ProductCard
    id={{}}
    color={{}}
    name={{}}
    image={{}}
    description={{}}
    offerPrice={{}}
    />
  );
}
```
---
## ProductPlaceholder (`COMP_PRODUCTPLACEHOLDER`)
- **File**: `frontend\src\ui-component\cards\Skeleton\ProductPlaceholder.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ProductPlaceholder from "ui-component/cards/Skeleton/ProductPlaceholder";

export default function Example() {
  return (
    <ProductPlaceholder
    />
  );
}
```
---
## ProductReview (`COMP_PRODUCTREVIEW`)
- **File**: `frontend\src\ui-component\cards\ProductReview.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `avatar` | `string` | no | — |
| `date` | `oneOfType` | no | — |
| `name` | `string` | no | — |
| `status` | `bool` | no | — |
| `rating` | `number` | no | — |
| `review` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ProductReview from "ui-component/cards/ProductReview";

export default function Example() {
  return (
    <ProductReview
    avatar="example"
    date={/* TODO */}
    name="example"
    status={false}
    rating={0}
    review="example"
    />
  );
}
```
---
## ProductSales (`COMP_PRODUCTSALES`)
- **File**: `frontend\src\views\widget\Data\ProductSales.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ProductSales from "views/widget/Data/ProductSales";

export default function Example() {
  return (
    <ProductSales
    />
  );
}
```
---
## ProfitEmojiIcon (`COMP_PROFITEMOJIICON`)
- **File**: `frontend\src\views\alertThresholds\icons.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ProfitEmojiIcon from "views/alertThresholds/icons";

export default function Example() {
  return (
    <ProfitEmojiIcon
    />
  );
}
```
---
## ProfitMonitorCard (`COMP_PROFITMONITORCARD`)
- **File**: `frontend\src\views\monitorManager\ProfitMonitorCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ProfitMonitorCard from "views/monitorManager/ProfitMonitorCard";

export default function Example() {
  return (
    <ProfitMonitorCard
    />
  );
}
```
---
## ProfitRiskHeaderBadges (`COMP_PROFITRISKHEADERBADGES`)
- **File**: `frontend\src\components\ProfitRiskHeaderBadges.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ProfitRiskHeaderBadges from "components/ProfitRiskHeaderBadges";

export default function Example() {
  return (
    <ProfitRiskHeaderBadges
    />
  );
}
```
---
## ProjectTable (`COMP_PROJECTTABLE`)
- **File**: `frontend\src\views\widget\Data\ProjectTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ProjectTable from "views/widget/Data/ProjectTable";

export default function Example() {
  return (
    <ProjectTable
    />
  );
}
```
---
## ProjectTaskCard (`COMP_PROJECTTASKCARD`)
- **File**: `frontend\src\views\widget\Statistics\ProjectTaskCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ProjectTaskCard from "views/widget/Statistics/ProjectTaskCard";

export default function Example() {
  return (
    <ProjectTaskCard
    />
  );
}
```
---
## ProviderAccordion (`COMP_PROVIDERACCORDION`)
- **File**: `frontend\src\views\xcomSettings\components\ProviderAccordion.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ProviderAccordion from "views/xcomSettings/components/ProviderAccordion";

export default function Example() {
  return (
    <ProviderAccordion
    />
  );
}
```
---
## QuickFilter (`COMP_QUICKFILTER`)
- **File**: `frontend\src\views\forms\data-grid\QuickFilter\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import QuickFilter from "views/forms/data-grid/QuickFilter/index";

export default function Example() {
  return (
    <QuickFilter
    />
  );
}
```
---
## QuickFilteringCustomLogic (`COMP_QUICKFILTERINGCUSTOMLOGIC`)
- **File**: `frontend\src\views\forms\data-grid\QuickFilter\CustomFilter.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import QuickFilteringCustomLogic from "views/forms/data-grid/QuickFilter/CustomFilter";

export default function Example() {
  return (
    <QuickFilteringCustomLogic
    />
  );
}
```
---
## QuickFilteringInitialize (`COMP_QUICKFILTERINGINITIALIZE`)
- **File**: `frontend\src\views\forms\data-grid\QuickFilter\Initialize.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import QuickFilteringInitialize from "views/forms/data-grid/QuickFilter/Initialize";

export default function Example() {
  return (
    <QuickFilteringInitialize
    />
  );
}
```
---
## QuickImportStarWars (`COMP_QUICKIMPORTSTARWARS`)
- **File**: `frontend\src\views\traderShop\QuickImportStarWars.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import QuickImportStarWars from "views/traderShop/QuickImportStarWars";

export default function Example() {
  return (
    <QuickImportStarWars
    />
  );
}
```
---
## QuoteCard (`COMP_QUOTECARD`)
- **File**: `frontend\src\views\jupiter\JupiterPage.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import QuoteCard from "views/jupiter/JupiterPage";

export default function Example() {
  return (
    <QuoteCard
    />
  );
}
```
---
## RadioGroupForms (`COMP_RADIOGROUPFORMS`)
- **File**: `frontend\src\views\forms\forms-validation\RadioGroupForms.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import RadioGroupForms from "views/forms/forms-validation/RadioGroupForms";

export default function Example() {
  return (
    <RadioGroupForms
    />
  );
}
```
---
## RatingEditInputCell (`COMP_RATINGEDITINPUTCELL`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\CustomEdit.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import RatingEditInputCell from "views/forms/data-grid/InLineEditing/CustomEdit";

export default function Example() {
  return (
    <RatingEditInputCell
    />
  );
}
```
---
## RecaptchaPage (`COMP_RECAPTCHAPAGE`)
- **File**: `frontend\src\views\forms\plugins\Recaptcha.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import RecaptchaPage from "views/forms/plugins/Recaptcha";

export default function Example() {
  return (
    <RecaptchaPage
    />
  );
}
```
---
## RecentTickets (`COMP_RECENTTICKETS`)
- **File**: `frontend\src\views\widget\Data\RecentTickets.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import RecentTickets from "views/widget/Data/RecentTickets";

export default function Example() {
  return (
    <RecentTickets
    />
  );
}
```
---
## Register (`COMP_REGISTER`)
- **File**: `frontend\src\views\pages\authentication\Register.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Register from "views/pages/authentication/Register";

export default function Example() {
  return (
    <Register
    />
  );
}
```
---
## RejectionFiles (`COMP_REJECTIONFILES`)
- **File**: `frontend\src\ui-component\third-party\dropzone\RejectionFile.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `fileRejections` | `array` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import RejectionFiles from "ui-component/third-party/dropzone/RejectionFile";

export default function Example() {
  return (
    <RejectionFiles
    fileRejections={[]}
    />
  );
}
```
---
## ReorderMenu (`COMP_REORDERMENU`)
- **File**: `frontend\src\views\forms\data-grid\ColumnMenu\ReorderingMenu.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ReorderMenu from "views/forms/data-grid/ColumnMenu/ReorderingMenu";

export default function Example() {
  return (
    <ReorderMenu
    />
  );
}
```
---
## ReportCard (`COMP_REPORTCARD`)
- **File**: `frontend\src\ui-component\cards\ReportCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `primary` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ReportCard from "ui-component/cards/ReportCard";

export default function Example() {
  return (
    <ReportCard
    primary={{}}
    />
  );
}
```
---
## ResetPassword (`COMP_RESETPASSWORD`)
- **File**: `frontend\src\views\pages\authentication\ResetPassword.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ResetPassword from "views/pages/authentication/ResetPassword";

export default function Example() {
  return (
    <ResetPassword
    />
  );
}
```
---
## RevenueCard (`COMP_REVENUECARD`)
- **File**: `frontend\src\ui-component\cards\RevenueCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `primary` | `any` | no | — |
| `secondary` | `any` | no | — |
| `content` | `any` | no | — |
| `iconPrimary` | `any` | no | — |
| `color` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import RevenueCard from "ui-component/cards/RevenueCard";

export default function Example() {
  return (
    <RevenueCard
    primary={{}}
    secondary={{}}
    content={{}}
    iconPrimary={{}}
    color={{}}
    />
  );
}
```
---
## RevenueChartCard (`COMP_REVENUECHARTCARD`)
- **File**: `frontend\src\views\widget\Chart\RevenueChartCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `chartData` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import RevenueChartCard from "views/widget/Chart/RevenueChartCard";

export default function Example() {
  return (
    <RevenueChartCard
    chartData={{}}
    />
  );
}
```
---
## Review (`COMP_REVIEW`)
- **File**: `frontend\src\views\forms\forms-wizard\BasicWizard\Review.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Review from "views/forms/forms-wizard/BasicWizard/Review";

export default function Example() {
  return (
    <Review
    />
  );
}
```
---
## RoundIconCard (`COMP_ROUNDICONCARD`)
- **File**: `frontend\src\ui-component\cards\RoundIconCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `primary` | `string` | no | — |
| `secondary` | `string` | no | — |
| `content` | `string` | no | — |
| `iconPrimary` | `any` | no | — |
| `color` | `string` | no | — |
| `bgcolor` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import RoundIconCard from "ui-component/cards/RoundIconCard";

export default function Example() {
  return (
    <RoundIconCard
    primary="example"
    secondary="example"
    content="example"
    iconPrimary={{}}
    color="example"
    bgcolor="example"
    />
  );
}
```
---
## Row (`COMP_ROW`)
- **File**: `frontend\src\views\forms\tables\TableCollapsible.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `row` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Row from "views/forms/tables/TableCollapsible";

export default function Example() {
  return (
    <Row
    row={{}}
    />
  );
}
```
---
## RTLLayout (`COMP_RTLLAYOUT`)
- **File**: `frontend\src\ui-component\RTLLayout.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import RTLLayout from "ui-component/RTLLayout";

export default function Example() {
  return (
    <RTLLayout
    children="example"
    />
  );
}
```
---
## SalesLineChartCard (`COMP_SALESLINECHARTCARD`)
- **File**: `frontend\src\ui-component\cards\SalesLineChartCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `bgColor` | `string` | no | — |
| `chartData` | `any` | no | — |
| `footerData` | `object` | no | — |
| `icon` | `oneOfType` | no | — |
| `title` | `string` | no | — |
| `percentage` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SalesLineChartCard from "ui-component/cards/SalesLineChartCard";

export default function Example() {
  return (
    <SalesLineChartCard
    bgColor="example"
    chartData={{}}
    footerData={{}}
    icon={/* TODO */}
    title="example"
    percentage="example"
    />
  );
}
```
---
## SatisfactionChartCard (`COMP_SATISFACTIONCHARTCARD`)
- **File**: `frontend\src\views\widget\Chart\SatisfactionChartCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `chartData` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SatisfactionChartCard from "views/widget/Chart/SatisfactionChartCard";

export default function Example() {
  return (
    <SatisfactionChartCard
    chartData={{}}
    />
  );
}
```
---
## SaveRestoreState (`COMP_SAVERESTORESTATE`)
- **File**: `frontend\src\views\forms\data-grid\SaveRestoreState\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SaveRestoreState from "views/forms/data-grid/SaveRestoreState/index";

export default function Example() {
  return (
    <SaveRestoreState
    />
  );
}
```
---
## SearchSection (`COMP_SEARCHSECTION`)
- **File**: `frontend\src\layout\MainLayout\Header\SearchSection\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SearchSection from "layout/MainLayout/Header/SearchSection/index";

export default function Example() {
  return (
    <SearchSection
    />
  );
}
```
---
## Section (`COMP_SECTION`)
- **File**: `frontend\src\views\sonic\index.jsx`
- **Used by routes**: `/sonic`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Section from "views/sonic/index";

export default function Example() {
  return (
    <Section
    />
  );
}
```
---
## SelectEditInputCell (`COMP_SELECTEDITINPUTCELL`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\AutoStop.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SelectEditInputCell from "views/forms/data-grid/InLineEditing/AutoStop";

export default function Example() {
  return (
    <SelectEditInputCell
    />
  );
}
```
---
## SelectForms (`COMP_SELECTFORMS`)
- **File**: `frontend\src\views\forms\forms-validation\SelectForms.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SelectForms from "views/forms/forms-validation/SelectForms";

export default function Example() {
  return (
    <SelectForms
    />
  );
}
```
---
## SendCard (`COMP_SENDCARD`)
- **File**: `frontend\src\views\jupiter\JupiterPage.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SendCard from "views/jupiter/JupiterPage";

export default function Example() {
  return (
    <SendCard
    />
  );
}
```
---
## SeoChartCard (`COMP_SEOCHARTCARD`)
- **File**: `frontend\src\ui-component\cards\SeoChartCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `chartData` | `any` | no | — |
| `value` | `oneOfType` | no | — |
| `title` | `string` | no | — |
| `icon` | `oneOfType` | no | — |
| `type` | `number` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SeoChartCard from "ui-component/cards/SeoChartCard";

export default function Example() {
  return (
    <SeoChartCard
    chartData={{}}
    value={/* TODO */}
    title="example"
    icon={/* TODO */}
    type={0}
    />
  );
}
```
---
## ServerModal (`COMP_SERVERMODAL`)
- **File**: `frontend\src\views\forms\plugins\Modal\ServerModal.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ServerModal from "views/forms/plugins/Modal/ServerModal";

export default function Example() {
  return (
    <ServerModal
    />
  );
}
```
---
## ServerSidePersistence (`COMP_SERVERSIDEPERSISTENCE`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\ServerValidation.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ServerSidePersistence from "views/forms/data-grid/InLineEditing/ServerValidation";

export default function Example() {
  return (
    <ServerSidePersistence
    />
  );
}
```
---
## SettingsSection (`COMP_SETTINGSSECTION`)
- **File**: `frontend\src\layout\MainLayout\Header\SettingsSection\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SettingsSection from "layout/MainLayout/Header/SettingsSection/index";

export default function Example() {
  return (
    <SettingsSection
    />
  );
}
```
---
## ShadowBox (`COMP_SHADOWBOX`)
- **File**: `frontend\src\views\utilities\Shadow.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `shadow` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ShadowBox from "views/utilities/Shadow";

export default function Example() {
  return (
    <ShadowBox
    shadow="example"
    />
  );
}
```
---
## Sidebar (`COMP_SIDEBAR`)
- **File**: `frontend\src\layout\MainLayout\Sidebar\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Sidebar from "layout/MainLayout/Sidebar/index";

export default function Example() {
  return (
    <Sidebar
    />
  );
}
```
---
## SidebarDrawer (`COMP_SIDEBARDRAWER`)
- **File**: `frontend\src\layout\Customization\SidebarDrawer.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SidebarDrawer from "layout/Customization/SidebarDrawer";

export default function Example() {
  return (
    <SidebarDrawer
    />
  );
}
```
---
## SideIconCard (`COMP_SIDEICONCARD`)
- **File**: `frontend\src\ui-component\cards\SideIconCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `iconPrimary` | `object` | no | — |
| `primary` | `any` | no | — |
| `secondary` | `any` | no | — |
| `secondarySub` | `string` | no | — |
| `color` | `any` | no | — |
| `bgcolor` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SideIconCard from "ui-component/cards/SideIconCard";

export default function Example() {
  return (
    <SideIconCard
    iconPrimary={{}}
    primary={{}}
    secondary={{}}
    secondarySub="example"
    color={{}}
    bgcolor="example"
    />
  );
}
```
---
## SidePanelWidthSlider (`COMP_SIDEPANELWIDTHSLIDER`)
- **File**: `frontend\src\views\positions\SidePanelWidthSlider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SidePanelWidthSlider from "views/positions/SidePanelWidthSlider";

export default function Example() {
  return (
    <SidePanelWidthSlider
    />
  );
}
```
---
## SimpleModal (`COMP_SIMPLEMODAL`)
- **File**: `frontend\src\views\forms\plugins\Modal\SimpleModal.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SimpleModal from "views/forms/plugins/Modal/SimpleModal";

export default function Example() {
  return (
    <SimpleModal
    />
  );
}
```
---
## SimpleTree (`COMP_SIMPLETREE`)
- **File**: `frontend\src\views\forms\chart\OrgChart\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `name` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SimpleTree from "views/forms/chart/OrgChart/index";

export default function Example() {
  return (
    <SimpleTree
    name={{}}
    />
  );
}
```
---
## SingleFileUpload (`COMP_SINGLEFILEUPLOAD`)
- **File**: `frontend\src\ui-component\third-party\dropzone\SingleFile.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `error` | `any` | no | — |
| `file` | `any` | no | — |
| `setFieldValue` | `any` | no | — |
| `sx` | `any` | no | — |
| `other` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SingleFileUpload from "ui-component/third-party/dropzone/SingleFile";

export default function Example() {
  return (
    <SingleFileUpload
    error={{}}
    file={{}}
    setFieldValue={{}}
    sx={{}}
    other={{}}
    />
  );
}
```
---
## SkypeIcon (`COMP_SKYPEICON`)
- **File**: `frontend\src\views\forms\chart\OrgChart\SkypeIcon.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SkypeIcon from "views/forms/chart/OrgChart/SkypeIcon";

export default function Example() {
  return (
    <SkypeIcon
    />
  );
}
```
---
## Slider (`COMP_SLIDER`)
- **File**: `frontend\src\views\forms\components\Slider\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Slider from "views/forms/components/Slider/index";

export default function Example() {
  return (
    <Slider
    />
  );
}
```
---
## Snackbar (`COMP_SNACKBAR`)
- **File**: `frontend\src\ui-component\extended\Snackbar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Snackbar from "ui-component/extended/Snackbar";

export default function Example() {
  return (
    <Snackbar
    />
  );
}
```
---
## SnackBarAction (`COMP_SNACKBARACTION`)
- **File**: `frontend\src\ui-component\extended\notistack\SnackBarAction.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SnackBarAction from "ui-component/extended/notistack/SnackBarAction";

export default function Example() {
  return (
    <SnackBarAction
    />
  );
}
```
---
## Sonic (`COMP_SONIC`)
- **File**: `frontend\src\views\sonic\index.jsx`
- **Used by routes**: `/sonic`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Sonic from "views/sonic/index";

export default function Example() {
  return (
    <Sonic
    />
  );
}
```
---
## SonicLabsPage (`COMP_SONICLABSPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SonicLabsPage from "routes/MainRoutes";

export default function Example() {
  return (
    <SonicLabsPage
    />
  );
}
```
---
## SonicMonitorCard (`COMP_SONICMONITORCARD`)
- **File**: `frontend\src\views\monitorManager\SonicMonitorCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SonicMonitorCard from "views/monitorManager/SonicMonitorCard";

export default function Example() {
  return (
    <SonicMonitorCard
    />
  );
}
```
---
## SpacingGrid (`COMP_SPACINGGRID`)
- **File**: `frontend\src\views\utilities\Grid\SpacingGrid.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SpacingGrid from "views/utilities/Grid/SpacingGrid";

export default function Example() {
  return (
    <SpacingGrid
    />
  );
}
```
---
## StartEditButtonGrid (`COMP_STARTEDITBUTTONGRID`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\Controlled.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import StartEditButtonGrid from "views/forms/data-grid/InLineEditing/Controlled";

export default function Example() {
  return (
    <StartEditButtonGrid
    />
  );
}
```
---
## StatCard (`COMP_STATCARD`)
- **File**: `frontend\src\components\old\StatCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `icon` | `node` | no | — |
| `label` | `string` | no | — |
| `value` | `any` | no | — |
| `secondary` | `any` | no | — |
| `variant` | `oneOf` | no | — |
| `onClick` | `func` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import StatCard from "components/old/StatCard";

export default function Example() {
  return (
    <StatCard
    icon="example"
    label="example"
    value={{}}
    secondary={{}}
    variant={/* TODO */}
    onClick={/* TODO */}
    />
  );
}
```
---
## StatusCard (`COMP_STATUSCARD`)
- **File**: `frontend\src\ui-component\status-rail\StatusCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `front` | `shape` | no | — |
| `icon` | `node` | no | — |
| `color` | `string` | no | — |
| `label` | `string` | no | — |
| `value` | `oneOfType` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import StatusCard from "ui-component/status-rail/StatusCard";

export default function Example() {
  return (
    <StatusCard
    front={/* TODO */}
    icon="example"
    color="example"
    label="example"
    value={/* TODO */}
    />
  );
}
```
---
## StatusCell (`COMP_STATUSCELL`)
- **File**: `frontend\src\ui-component\wallet\WalletTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import StatusCell from "ui-component/wallet/WalletTable";

export default function Example() {
  return (
    <StatusCell
    />
  );
}
```
---
## StatusRail (`COMP_STATUSRAIL`)
- **File**: `frontend\src\components\StatusRail\StatusRail.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `cards` | `array` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import StatusRail from "components/StatusRail/StatusRail";

export default function Example() {
  return (
    <StatusRail
    cards={[]}
    />
  );
}
```
---
## StepCard (`COMP_STEPCARD`)
- **File**: `frontend\src\views\sonicLabs\SonicLabsPage.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import StepCard from "views/sonicLabs/SonicLabsPage";

export default function Example() {
  return (
    <StepCard
    />
  );
}
```
---
## StepSlider (`COMP_STEPSLIDER`)
- **File**: `frontend\src\views\forms\components\Slider\StepSlider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import StepSlider from "views/forms/components/Slider/StepSlider";

export default function Example() {
  return (
    <StepSlider
    />
  );
}
```
---
## StickyActionBar (`COMP_STICKYACTIONBAR`)
- **File**: `frontend\src\views\forms\layouts\StickyActionBar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import StickyActionBar from "views/forms/layouts/StickyActionBar";

export default function Example() {
  return (
    <StickyActionBar
    />
  );
}
```
---
## StickyHeadTable (`COMP_STICKYHEADTABLE`)
- **File**: `frontend\src\views\forms\tables\TableStickyHead.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import StickyHeadTable from "views/forms/tables/TableStickyHead";

export default function Example() {
  return (
    <StickyHeadTable
    />
  );
}
```
---
## StoryComment (`COMP_STORYCOMMENT`)
- **File**: `frontend\src\views\kanban\Backlogs\StoryComment.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `comment` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import StoryComment from "views/kanban/Backlogs/StoryComment";

export default function Example() {
  return (
    <StoryComment
    comment={{}}
    />
  );
}
```
---
## SubCard (`COMP_SUBCARD`)
- **File**: `frontend\src\ui-component\cards\SubCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `oneOfType` | no | — |
| `className` | `string` | no | — |
| `content` | `bool` | no | — |
| `contentClass` | `string` | no | — |
| `darkTitle` | `bool` | no | — |
| `secondary` | `oneOfType` | no | — |
| `sx` | `object` | no | — |
| `contentSX` | `object` | no | — |
| `footerSX` | `object` | no | — |
| `title` | `oneOfType` | no | — |
| `actions` | `oneOfType` | no | — |
| `others` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SubCard from "ui-component/cards/SubCard";

export default function Example() {
  return (
    <SubCard
    children={/* TODO */}
    className="example"
    content={false}
    contentClass="example"
    darkTitle={false}
    secondary={/* TODO */}
    />
  );
}
```
---
## SupabaseLogin (`COMP_SUPABASELOGIN`)
- **File**: `frontend\src\views\pages\authentication\supabase\AuthLogin.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SupabaseLogin from "views/pages/authentication/supabase/AuthLogin";

export default function Example() {
  return (
    <SupabaseLogin
    />
  );
}
```
---
## SupabaseRegister (`COMP_SUPABASEREGISTER`)
- **File**: `frontend\src\views\pages\authentication\supabase\AuthRegister.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SupabaseRegister from "views/pages/authentication/supabase/AuthRegister";

export default function Example() {
  return (
    <SupabaseRegister
    />
  );
}
```
---
## SupabseProvider (`COMP_SUPABSEPROVIDER`)
- **File**: `frontend\src\contexts\SupabaseContext.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SupabseProvider from "contexts/SupabaseContext";

export default function Example() {
  return (
    <SupabseProvider
    children="example"
    />
  );
}
```
---
## SwapsTab (`COMP_SWAPSTAB`)
- **File**: `frontend\src\views\jupiter\JupiterPage.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import SwapsTab from "views/jupiter/JupiterPage";

export default function Example() {
  return (
    <SwapsTab
    />
  );
}
```
---
## TableBasic (`COMP_TABLEBASIC`)
- **File**: `frontend\src\views\forms\tables\TableBasic.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TableBasic from "views/forms/tables/TableBasic";

export default function Example() {
  return (
    <TableBasic
    />
  );
}
```
---
## TableCollapsible (`COMP_TABLECOLLAPSIBLE`)
- **File**: `frontend\src\views\forms\tables\TableCollapsible.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TableCollapsible from "views/forms/tables/TableCollapsible";

export default function Example() {
  return (
    <TableCollapsible
    />
  );
}
```
---
## TableDataGrid (`COMP_TABLEDATAGRID`)
- **File**: `frontend\src\views\forms\data-grid\DataGridBasic\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `Selected` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TableDataGrid from "views/forms/data-grid/DataGridBasic/index";

export default function Example() {
  return (
    <TableDataGrid
    Selected={{}}
    />
  );
}
```
---
## TasksCard (`COMP_TASKSCARD`)
- **File**: `frontend\src\views\widget\Data\TasksCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TasksCard from "views/widget/Data/TasksCard";

export default function Example() {
  return (
    <TasksCard
    />
  );
}
```
---
## TeamMembers (`COMP_TEAMMEMBERS`)
- **File**: `frontend\src\views\widget\Data\TeamMembers.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TeamMembers from "views/widget/Data/TeamMembers";

export default function Example() {
  return (
    <TeamMembers
    />
  );
}
```
---
## TextFieldPage (`COMP_TEXTFIELDPAGE`)
- **File**: `frontend\src\views\forms\components\TextField.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TextFieldPage from "views/forms/components/TextField";

export default function Example() {
  return (
    <TextFieldPage
    />
  );
}
```
---
## ThemeCustomization (`COMP_THEMECUSTOMIZATION`)
- **File**: `frontend\src\themes\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ThemeCustomization from "themes/index";

export default function Example() {
  return (
    <ThemeCustomization
    children="example"
    />
  );
}
```
---
## ThemeLab (`COMP_THEMELAB`)
- **File**: `frontend\src\views\labs\ThemeLab.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ThemeLab from "views/labs/ThemeLab";

export default function Example() {
  return (
    <ThemeLab
    />
  );
}
```
---
## ThemeLabPage (`COMP_THEMELABPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ThemeLabPage from "routes/MainRoutes";

export default function Example() {
  return (
    <ThemeLabPage
    />
  );
}
```
---
## ThemeModeLayout (`COMP_THEMEMODELAYOUT`)
- **File**: `frontend\src\layout\Customization\ThemeMode.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ThemeModeLayout from "layout/Customization/ThemeMode";

export default function Example() {
  return (
    <ThemeModeLayout
    />
  );
}
```
---
## ThemeModeSection (`COMP_THEMEMODESECTION`)
- **File**: `frontend\src\layout\MainLayout\Header\ThemeModeSection\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ThemeModeSection from "layout/MainLayout/Header/ThemeModeSection/index";

export default function Example() {
  return (
    <ThemeModeSection
    />
  );
}
```
---
## ThresholdsTable (`COMP_THRESHOLDSTABLE`)
- **File**: `frontend\src\views\alertThresholds\ThresholdsTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ThresholdsTable from "views/alertThresholds/ThresholdsTable";

export default function Example() {
  return (
    <ThresholdsTable
    />
  );
}
```
---
## ThresholdTable (`COMP_THRESHOLDTABLE`)
- **File**: `frontend\src\ui-component\thresholds\ThresholdTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ThresholdTable from "ui-component/thresholds/ThresholdTable";

export default function Example() {
  return (
    <ThresholdTable
    />
  );
}
```
---
## TimerSection (`COMP_TIMERSECTION`)
- **File**: `frontend\src\layout\MainLayout\Header\TimerSection\TimerSection.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TimerSection from "layout/MainLayout/Header/TimerSection/TimerSection";

export default function Example() {
  return (
    <TimerSection
    />
  );
}
```
---
## ToDoList (`COMP_TODOLIST`)
- **File**: `frontend\src\views\widget\Data\ToDoList.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ToDoList from "views/widget/Data/ToDoList";

export default function Example() {
  return (
    <ToDoList
    />
  );
}
```
---
## Toolbar (`COMP_TOOLBAR`)
- **File**: `frontend\src\views\forms\data-grid\SaveRestoreState\UseGridSelector.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Toolbar from "views/forms/data-grid/SaveRestoreState/UseGridSelector";

export default function Example() {
  return (
    <Toolbar
    />
  );
}
```
---
## Tooltip (`COMP_TOOLTIP`)
- **File**: `frontend\src\views\forms\plugins\Tooltip.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Tooltip from "views/forms/plugins/Tooltip";

export default function Example() {
  return (
    <Tooltip
    />
  );
}
```
---
## TopCell (`COMP_TOPCELL`)
- **File**: `frontend\src\ui-component\wallet\WalletTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TopCell from "ui-component/wallet/WalletTable";

export default function Example() {
  return (
    <TopCell
    />
  );
}
```
---
## TopTokensChips (`COMP_TOPTOKENSCHIPS`)
- **File**: `frontend\src\components\wallets\VerifiedCells.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TopTokensChips from "components/wallets/VerifiedCells";

export default function Example() {
  return (
    <TopTokensChips
    />
  );
}
```
---
## TotalGrowthBarChart (`COMP_TOTALGROWTHBARCHART`)
- **File**: `frontend\src\ui-component\cards\Skeleton\TotalGrowthBarChart.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `isLoading` | `bool` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TotalGrowthBarChart from "ui-component/cards/Skeleton/TotalGrowthBarChart";

export default function Example() {
  return (
    <TotalGrowthBarChart
    isLoading={false}
    />
  );
}
```
---
## TotalIncomeCard (`COMP_TOTALINCOMECARD`)
- **File**: `frontend\src\ui-component\cards\Skeleton\TotalIncomeCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TotalIncomeCard from "ui-component/cards/Skeleton/TotalIncomeCard";

export default function Example() {
  return (
    <TotalIncomeCard
    />
  );
}
```
---
## TotalIncomeDarkCard (`COMP_TOTALINCOMEDARKCARD`)
- **File**: `frontend\src\ui-component\cards\TotalIncomeDarkCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `isLoading` | `bool` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TotalIncomeDarkCard from "ui-component/cards/TotalIncomeDarkCard";

export default function Example() {
  return (
    <TotalIncomeDarkCard
    isLoading={false}
    />
  );
}
```
---
## TotalIncomeLightCard (`COMP_TOTALINCOMELIGHTCARD`)
- **File**: `frontend\src\ui-component\cards\TotalIncomeLightCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `isLoading` | `bool` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TotalIncomeLightCard from "ui-component/cards/TotalIncomeLightCard";

export default function Example() {
  return (
    <TotalIncomeLightCard
    isLoading={false}
    />
  );
}
```
---
## TotalLineChartCard (`COMP_TOTALLINECHARTCARD`)
- **File**: `frontend\src\ui-component\cards\TotalLineChartCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `bgColor` | `string` | no | — |
| `chartData` | `any` | no | — |
| `title` | `string` | no | — |
| `percentage` | `string` | no | — |
| `value` | `number` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TotalLineChartCard from "ui-component/cards/TotalLineChartCard";

export default function Example() {
  return (
    <TotalLineChartCard
    bgColor="example"
    chartData={{}}
    title="example"
    percentage="example"
    value={0}
    />
  );
}
```
---
## TotalOrderLineChartCard (`COMP_TOTALORDERLINECHARTCARD`)
- **File**: `frontend\src\views\dashboard\Default\TotalOrderLineChartCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `isLoading` | `bool` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TotalOrderLineChartCard from "views/dashboard/Default/TotalOrderLineChartCard";

export default function Example() {
  return (
    <TotalOrderLineChartCard
    isLoading={false}
    />
  );
}
```
---
## TotalRevenue (`COMP_TOTALREVENUE`)
- **File**: `frontend\src\views\widget\Data\TotalRevenue.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TotalRevenue from "views/widget/Data/TotalRevenue";

export default function Example() {
  return (
    <TotalRevenue
    />
  );
}
```
---
## TotalValueCard (`COMP_TOTALVALUECARD`)
- **File**: `frontend\src\ui-component\cards\TotalValueCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `primary` | `any` | no | — |
| `secondary` | `any` | no | — |
| `content` | `any` | no | — |
| `iconPrimary` | `any` | no | — |
| `color` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TotalValueCard from "ui-component/cards/TotalValueCard";

export default function Example() {
  return (
    <TotalValueCard
    primary={{}}
    secondary={{}}
    content={{}}
    iconPrimary={{}}
    color={{}}
    />
  );
}
```
---
## TraderBar (`COMP_TRADERBAR`)
- **File**: `frontend\src\views\traderFactory\TraderBar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TraderBar from "views/traderFactory/TraderBar";

export default function Example() {
  return (
    <TraderBar
    />
  );
}
```
---
## TraderCard (`COMP_TRADERCARD`)
- **File**: `frontend\src\views\traderFactory\TraderCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `trader` | `object` | yes | — |
| `onDelete` | `func` | yes | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TraderCard from "views/traderFactory/TraderCard";

export default function Example() {
  return (
    <TraderCard
    trader={{}}
    onDelete={/* TODO */}
    />
  );
}
```
---
## TraderEnhancedTable (`COMP_TRADERENHANCEDTABLE`)
- **File**: `frontend\src\views\traderShop\TraderEnhancedTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `headCells` | `array` | yes | — |
| `rows` | `array` | yes | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TraderEnhancedTable from "views/traderShop/TraderEnhancedTable";

export default function Example() {
  return (
    <TraderEnhancedTable
    headCells={[]}
    rows={[]}
    />
  );
}
```
---
## TraderEnhancedTableHead (`COMP_TRADERENHANCEDTABLEHEAD`)
- **File**: `frontend\src\views\traderShop\TraderEnhancedTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TraderEnhancedTableHead from "views/traderShop/TraderEnhancedTable";

export default function Example() {
  return (
    <TraderEnhancedTableHead
    />
  );
}
```
---
## TraderFactoryPage (`COMP_TRADERFACTORYPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TraderFactoryPage from "routes/MainRoutes";

export default function Example() {
  return (
    <TraderFactoryPage
    />
  );
}
```
---
## TraderFormDrawer (`COMP_TRADERFORMDRAWER`)
- **File**: `frontend\src\views\traderShop\TraderFormDrawer.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `open` | `bool` | no | — |
| `onClose` | `func` | no | — |
| `initial` | `object` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TraderFormDrawer from "views/traderShop/TraderFormDrawer";

export default function Example() {
  return (
    <TraderFormDrawer
    open={false}
    onClose={/* TODO */}
    initial={{}}
    />
  );
}
```
---
## TraderListCard (`COMP_TRADERLISTCARD`)
- **File**: `frontend\src\components\TraderListCard\TraderListCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `title` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TraderListCard from "components/TraderListCard/TraderListCard";

export default function Example() {
  return (
    <TraderListCard
    title="example"
    />
  );
}
```
---
## TraderShopIndex (`COMP_TRADERSHOPINDEX`)
- **File**: `frontend\src\routes\TraderShopRoutes.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TraderShopIndex from "routes/TraderShopRoutes";

export default function Example() {
  return (
    <TraderShopIndex
    />
  );
}
```
---
## TraderShopList (`COMP_TRADERSHOPLIST`)
- **File**: `frontend\src\views\traderShop\TraderShopList.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TraderShopList from "views/traderShop/TraderShopList";

export default function Example() {
  return (
    <TraderShopList
    />
  );
}
```
---
## TrafficSources (`COMP_TRAFFICSOURCES`)
- **File**: `frontend\src\views\widget\Data\TrafficSources.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TrafficSources from "views/widget/Data/TrafficSources";

export default function Example() {
  return (
    <TrafficSources
    />
  );
}
```
---
## TransactionCard (`COMP_TRANSACTIONCARD`)
- **File**: `frontend\src\views\jupiter\JupiterPage.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TransactionCard from "views/jupiter/JupiterPage";

export default function Example() {
  return (
    <TransactionCard
    />
  );
}
```
---
## TransitionBar (`COMP_TRANSITIONBAR`)
- **File**: `frontend\src\ui-component\extended\notistack\TransitionBar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TransitionBar from "ui-component/extended/notistack/TransitionBar";

export default function Example() {
  return (
    <TransitionBar
    />
  );
}
```
---
## Transitions (`COMP_TRANSITIONS`)
- **File**: `frontend\src\ui-component\extended\Transitions.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `children` | `node` | no | — |
| `position` | `string` | no | — |
| `sx` | `any` | no | — |
| `type` | `string` | no | — |
| `direction` | `oneOf` | no | — |
| `others` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Transitions from "ui-component/extended/Transitions";

export default function Example() {
  return (
    <Transitions
    children="example"
    position="example"
    sx={{}}
    type="example"
    direction={/* TODO */}
    others={{}}
    />
  );
}
```
---
## TransitionSlideDown (`COMP_TRANSITIONSLIDEDOWN`)
- **File**: `frontend\src\ui-component\extended\Snackbar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TransitionSlideDown from "ui-component/extended/Snackbar";

export default function Example() {
  return (
    <TransitionSlideDown
    />
  );
}
```
---
## TransitionSlideLeft (`COMP_TRANSITIONSLIDELEFT`)
- **File**: `frontend\src\ui-component\extended\Snackbar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TransitionSlideLeft from "ui-component/extended/Snackbar";

export default function Example() {
  return (
    <TransitionSlideLeft
    />
  );
}
```
---
## TransitionSlideRight (`COMP_TRANSITIONSLIDERIGHT`)
- **File**: `frontend\src\ui-component\extended\Snackbar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TransitionSlideRight from "ui-component/extended/Snackbar";

export default function Example() {
  return (
    <TransitionSlideRight
    />
  );
}
```
---
## TransitionSlideUp (`COMP_TRANSITIONSLIDEUP`)
- **File**: `frontend\src\ui-component\extended\Snackbar.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TransitionSlideUp from "ui-component/extended/Snackbar";

export default function Example() {
  return (
    <TransitionSlideUp
    />
  );
}
```
---
## TreeCard (`COMP_TREECARD`)
- **File**: `frontend\src\views\forms\chart\OrgChart\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `items` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import TreeCard from "views/forms/chart/OrgChart/index";

export default function Example() {
  return (
    <TreeCard
    items={{}}
    />
  );
}
```
---
## Typography (`COMP_TYPOGRAPHY`)
- **File**: `frontend\src\themes\typography.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import Typography from "themes/typography";

export default function Example() {
  return (
    <Typography
    />
  );
}
```
---
## UIButton (`COMP_UIBUTTON`)
- **File**: `frontend\src\views\forms\components\Button.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UIButton from "views/forms/components/Button";

export default function Example() {
  return (
    <UIButton
    />
  );
}
```
---
## UICheckbox (`COMP_UICHECKBOX`)
- **File**: `frontend\src\views\forms\components\Checkbox.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UICheckbox from "views/forms/components/Checkbox";

export default function Example() {
  return (
    <UICheckbox
    />
  );
}
```
---
## UIColor (`COMP_UICOLOR`)
- **File**: `frontend\src\views\utilities\Color.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UIColor from "views/utilities/Color";

export default function Example() {
  return (
    <UIColor
    />
  );
}
```
---
## UIRadio (`COMP_UIRADIO`)
- **File**: `frontend\src\views\forms\components\Radio.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UIRadio from "views/forms/components/Radio";

export default function Example() {
  return (
    <UIRadio
    />
  );
}
```
---
## UISwitch (`COMP_UISWITCH`)
- **File**: `frontend\src\views\forms\components\Switch.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UISwitch from "views/forms/components/Switch";

export default function Example() {
  return (
    <UISwitch
    />
  );
}
```
---
## UnderConstruction (`COMP_UNDERCONSTRUCTION`)
- **File**: `frontend\src\views\pages\maintenance\UnderConstruction.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UnderConstruction from "views/pages/maintenance/UnderConstruction";

export default function Example() {
  return (
    <UnderConstruction
    />
  );
}
```
---
## UpgradePlanCard (`COMP_UPGRADEPLANCARD`)
- **File**: `frontend\src\layout\MainLayout\Header\SettingsSection\UpgradePlanCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UpgradePlanCard from "layout/MainLayout/Header/SettingsSection/UpgradePlanCard";

export default function Example() {
  return (
    <UpgradePlanCard
    />
  );
}
```
---
## UseGridSelector (`COMP_USEGRIDSELECTOR`)
- **File**: `frontend\src\views\forms\data-grid\SaveRestoreState\UseGridSelector.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UseGridSelector from "views/forms/data-grid/SaveRestoreState/UseGridSelector";

export default function Example() {
  return (
    <UseGridSelector
    />
  );
}
```
---
## UserActivity (`COMP_USERACTIVITY`)
- **File**: `frontend\src\views\widget\Data\UserActivity.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UserActivity from "views/widget/Data/UserActivity";

export default function Example() {
  return (
    <UserActivity
    />
  );
}
```
---
## UserCountCard (`COMP_USERCOUNTCARD`)
- **File**: `frontend\src\ui-component\cards\UserCountCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `primary` | `string` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UserCountCard from "ui-component/cards/UserCountCard";

export default function Example() {
  return (
    <UserCountCard
    primary="example"
    />
  );
}
```
---
## UserDetailsCard (`COMP_USERDETAILSCARD`)
- **File**: `frontend\src\ui-component\cards\UserDetailsCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `about` | `any` | no | — |
| `avatar` | `any` | no | — |
| `contact` | `any` | no | — |
| `email` | `any` | no | — |
| `location` | `any` | no | — |
| `name` | `any` | no | — |
| `role` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UserDetailsCard from "ui-component/cards/UserDetailsCard";

export default function Example() {
  return (
    <UserDetailsCard
    about={{}}
    avatar={{}}
    contact={{}}
    email={{}}
    location={{}}
    name={{}}
    />
  );
}
```
---
## UserProfileCard (`COMP_USERPROFILECARD`)
- **File**: `frontend\src\ui-component\cards\UserProfileCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `avatar` | `any` | no | — |
| `name` | `any` | no | — |
| `profile` | `any` | no | — |
| `role` | `any` | no | — |
| `status` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UserProfileCard from "ui-component/cards/UserProfileCard";

export default function Example() {
  return (
    <UserProfileCard
    avatar={{}}
    name={{}}
    profile={{}}
    role={{}}
    status={{}}
    />
  );
}
```
---
## UserSimpleCard (`COMP_USERSIMPLECARD`)
- **File**: `frontend\src\ui-component\cards\UserSimpleCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `avatar` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UserSimpleCard from "ui-component/cards/UserSimpleCard";

export default function Example() {
  return (
    <UserSimpleCard
    avatar={{}}
    />
  );
}
```
---
## UserStory (`COMP_USERSTORY`)
- **File**: `frontend\src\views\kanban\Backlogs\UserStory.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
| Prop | Type | Required | Default |
|------|------|----------|---------|
| `story` | `any` | no | — |

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UserStory from "views/kanban/Backlogs/UserStory";

export default function Example() {
  return (
    <UserStory
    story={{}}
    />
  );
}
```
---
## UtilitiesShadow (`COMP_UTILITIESSHADOW`)
- **File**: `frontend\src\views\utilities\Shadow.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import UtilitiesShadow from "views/utilities/Shadow";

export default function Example() {
  return (
    <UtilitiesShadow
    />
  );
}
```
---
## ValidateServerNameGrid (`COMP_VALIDATESERVERNAMEGRID`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\Validation.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ValidateServerNameGrid from "views/forms/data-grid/InLineEditing/Validation";

export default function Example() {
  return (
    <ValidateServerNameGrid
    />
  );
}
```
---
## ValidationWizard (`COMP_VALIDATIONWIZARD`)
- **File**: `frontend\src\views\forms\forms-wizard\ValidationWizard\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ValidationWizard from "views/forms/forms-wizard/ValidationWizard/index";

export default function Example() {
  return (
    <ValidationWizard
    />
  );
}
```
---
## ValueParserSetterGrid (`COMP_VALUEPARSERSETTERGRID`)
- **File**: `frontend\src\views\forms\data-grid\InLineEditing\ParserSetter.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ValueParserSetterGrid from "views/forms/data-grid/InLineEditing/ParserSetter";

export default function Example() {
  return (
    <ValueParserSetterGrid
    />
  );
}
```
---
## ValueToCollateralChartCard (`COMP_VALUETOCOLLATERALCHARTCARD`)
- **File**: `frontend\src\ui-component\cards\ValueToCollateralChartCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ValueToCollateralChartCard from "ui-component/cards/ValueToCollateralChartCard";

export default function Example() {
  return (
    <ValueToCollateralChartCard
    />
  );
}
```
---
## VerifiedCell (`COMP_VERIFIEDCELL`)
- **File**: `frontend\src\ui-component\wallet\WalletTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import VerifiedCell from "ui-component/wallet/WalletTable";

export default function Example() {
  return (
    <VerifiedCell
    />
  );
}
```
---
## VerifiedSolCell (`COMP_VERIFIEDSOLCELL`)
- **File**: `frontend\src\components\wallets\VerifiedCells.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import VerifiedSolCell from "components/wallets/VerifiedCells";

export default function Example() {
  return (
    <VerifiedSolCell
    />
  );
}
```
---
## VerifiedStatusCell (`COMP_VERIFIEDSTATUSCELL`)
- **File**: `frontend\src\components\wallets\VerifiedCells.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import VerifiedStatusCell from "components/wallets/VerifiedCells";

export default function Example() {
  return (
    <VerifiedStatusCell
    />
  );
}
```
---
## VerticalMonitorSummaryCard (`COMP_VERTICALMONITORSUMMARYCARD`)
- **File**: `frontend\src\views\dashboard\VerticalMonitorSummaryCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import VerticalMonitorSummaryCard from "views/dashboard/VerticalMonitorSummaryCard";

export default function Example() {
  return (
    <VerticalMonitorSummaryCard
    />
  );
}
```
---
## VerticalSlider (`COMP_VERTICALSLIDER`)
- **File**: `frontend\src\views\forms\components\Slider\VerticalSlider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import VerticalSlider from "views/forms/components/Slider/VerticalSlider";

export default function Example() {
  return (
    <VerticalSlider
    />
  );
}
```
---
## ViewOnlyAlert (`COMP_VIEWONLYALERT`)
- **File**: `frontend\src\views\pages\authentication\ViewOnlyAlert.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ViewOnlyAlert from "views/pages/authentication/ViewOnlyAlert";

export default function Example() {
  return (
    <ViewOnlyAlert
    />
  );
}
```
---
## ViewRendererDateTime (`COMP_VIEWRENDERERDATETIME`)
- **File**: `frontend\src\views\forms\components\DateTime\ViewRendererDateTime.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ViewRendererDateTime from "views/forms/components/DateTime/ViewRendererDateTime";

export default function Example() {
  return (
    <ViewRendererDateTime
    />
  );
}
```
---
## ViewsDateTimePicker (`COMP_VIEWSDATETIMEPICKER`)
- **File**: `frontend\src\views\forms\components\DateTime\ViewsDateTimePicker.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import ViewsDateTimePicker from "views/forms/components/DateTime/ViewsDateTimePicker";

export default function Example() {
  return (
    <ViewsDateTimePicker
    />
  );
}
```
---
## VisibleColumnsModelControlled (`COMP_VISIBLECOLUMNSMODELCONTROLLED`)
- **File**: `frontend\src\views\forms\data-grid\ColumnVisibility\ControlledVisibility.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import VisibleColumnsModelControlled from "views/forms/data-grid/ColumnVisibility/ControlledVisibility";

export default function Example() {
  return (
    <VisibleColumnsModelControlled
    />
  );
}
```
---
## VisibleColumnsModelInitialState (`COMP_VISIBLECOLUMNSMODELINITIALSTATE`)
- **File**: `frontend\src\views\forms\data-grid\ColumnVisibility\InitializeColumnVisibility.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import VisibleColumnsModelInitialState from "views/forms/data-grid/ColumnVisibility/InitializeColumnVisibility";

export default function Example() {
  return (
    <VisibleColumnsModelInitialState
    />
  );
}
```
---
## VolumeSlider (`COMP_VOLUMESLIDER`)
- **File**: `frontend\src\views\forms\components\Slider\VolumeSlider.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import VolumeSlider from "views/forms/components/Slider/VolumeSlider";

export default function Example() {
  return (
    <VolumeSlider
    />
  );
}
```
---
## WalletCard (`COMP_WALLETCARD`)
- **File**: `frontend\src\views\jupiter\JupiterPage.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import WalletCard from "views/jupiter/JupiterPage";

export default function Example() {
  return (
    <WalletCard
    />
  );
}
```
---
## WalletFormModal (`COMP_WALLETFORMMODAL`)
- **File**: `frontend\src\ui-component\wallet\WalletFormModal.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import WalletFormModal from "ui-component/wallet/WalletFormModal";

export default function Example() {
  return (
    <WalletFormModal
    />
  );
}
```
---
## WalletManager (`COMP_WALLETMANAGER`)
- **File**: `frontend\src\views\wallet\WalletManager.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import WalletManager from "views/wallet/WalletManager";

export default function Example() {
  return (
    <WalletManager
    />
  );
}
```
---
## WalletManagerPage (`COMP_WALLETMANAGERPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import WalletManagerPage from "routes/MainRoutes";

export default function Example() {
  return (
    <WalletManagerPage
    />
  );
}
```
---
## WalletPieCard (`COMP_WALLETPIECARD`)
- **File**: `frontend\src\ui-component\wallet\WalletPieCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import WalletPieCard from "ui-component/wallet/WalletPieCard";

export default function Example() {
  return (
    <WalletPieCard
    />
  );
}
```
---
## WalletTable (`COMP_WALLETTABLE`)
- **File**: `frontend\src\ui-component\wallet\WalletTable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import WalletTable from "ui-component/wallet/WalletTable";

export default function Example() {
  return (
    <WalletTable
    />
  );
}
```
---
## WeatherCard (`COMP_WEATHERCARD`)
- **File**: `frontend\src\views\widget\Statistics\WeatherCard.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import WeatherCard from "views/widget/Statistics/WeatherCard";

export default function Example() {
  return (
    <WeatherCard
    />
  );
}
```
---
## WidgetData (`COMP_WIDGETDATA`)
- **File**: `frontend\src\views\widget\Data\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import WidgetData from "views/widget/Data/index";

export default function Example() {
  return (
    <WidgetData
    />
  );
}
```
---
## WidgetStatistics (`COMP_WIDGETSTATISTICS`)
- **File**: `frontend\src\views\widget\Statistics\index.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import WidgetStatistics from "views/widget/Statistics/index";

export default function Example() {
  return (
    <WidgetStatistics
    />
  );
}
```
---
## WrappedComponent (`COMP_WRAPPEDCOMPONENT`)
- **File**: `frontend\src\ui-component\Loadable.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import WrappedComponent from "ui-component/Loadable";

export default function Example() {
  return (
    <WrappedComponent
    />
  );
}
```
---
## XComSettings (`COMP_XCOMSETTINGS`)
- **File**: `frontend\src\views\xcomSettings\XComSettings.jsx`
- **Used by routes**: _not referenced directly by a route_

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import XComSettings from "views/xcomSettings/XComSettings";

export default function Example() {
  return (
    <XComSettings
    />
  );
}
```
---
## XComSettingsPage (`COMP_XCOMSETTINGSPAGE`)
- **File**: `frontend\src\routes\MainRoutes.jsx`
- **Used by routes**: `/alert-thresholds`, `/apps/kanban`, `/communications/xcom`, `/dashboard/analytics`, `/dashboard/default`, `/hedge-report`, `/jupiter`, `/monitor-manager`, `/overview`, `/positions`, `/sonic-labs`, `/sonic-labs/theme-lab`, `/trader-factory`, `/wallet-manager`, `backlogs`, `board`, `debug/db`

**Props**
_No props documented._

**Example**
```jsx
// Adjust import per your alias setup (e.g., "@/...")
import XComSettingsPage from "routes/MainRoutes";

export default function Example() {
  return (
    <XComSettingsPage
    />
  );
}
```
---
