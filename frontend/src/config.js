export const DASHBOARD_PATH = '/sonic';
export const HORIZONTAL_MAX_ITEM = 7;
export const CYCLONE_REFRESH_DELAY_MS = 4000;

export let MenuOrientation;

(function (MenuOrientation) {
  MenuOrientation['VERTICAL'] = 'vertical';
  MenuOrientation['HORIZONTAL'] = 'horizontal';
})(MenuOrientation || (MenuOrientation = {}));

export let ThemeMode;

(function (ThemeMode) {
  ThemeMode['LIGHT'] = 'light';
  ThemeMode['DARK'] = 'dark';
})(ThemeMode || (ThemeMode = {}));

export let ThemeDirection;

(function (ThemeDirection) {
  ThemeDirection['LTR'] = 'ltr';
  ThemeDirection['RTL'] = 'rtl';
})(ThemeDirection || (ThemeDirection = {}));

export let AuthProvider;

(function (AuthProvider) {
  AuthProvider['JWT'] = 'jwt';
  AuthProvider['FIREBASE'] = 'firebase';
  AuthProvider['AUTH0'] = 'auth0';
  AuthProvider['AWS'] = 'aws';
  AuthProvider['SUPABASE'] = 'supabase';
})(AuthProvider || (AuthProvider = {}));

export let DropzopType;

(function (DropzopType) {
  DropzopType['default'] = 'DEFAULT';
  DropzopType['standard'] = 'STANDARD';
})(DropzopType || (DropzopType = {}));

export const APP_AUTH = AuthProvider.JWT;

const config = {
  menuOrientation: MenuOrientation.VERTICAL,
  miniDrawer: false,
  sidePanelWidth: 260,
  fontFamily: `'Roboto', sans-serif`,
  borderRadius: 8,
  outlinedFilled: true,
  mode: ThemeMode.LIGHT,
  sidePanelWidth: 320,
  presetColor: 'default',
  i18n: 'en',
  themeDirection: ThemeDirection.LTR,
  container: true,
  cycloneRefreshDelay: CYCLONE_REFRESH_DELAY_MS
};

export default config;
