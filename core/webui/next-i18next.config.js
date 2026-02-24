// @ts-check

/**
 * @type {import('next-i18next').UserConfig}
 */
module.exports = {
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'zh'],
    /*domains: [
      {
        domain: 'juniorit.ai',
        defaultLocale: 'en',
      },
      {
        domain: 'ai-coding.net',
        defaultLocale: 'zh',
      },
    ]*/
  },
  localePath:
    typeof window === 'undefined'
      ? require('path').resolve('./public/locales')
      : '/locales',
}