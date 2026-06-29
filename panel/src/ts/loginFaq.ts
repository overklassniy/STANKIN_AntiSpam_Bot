/**
 * Переключение видимости FAQ на странице входа.
 */

/**
 * Инициализирует переключатель видимости блока FAQ.
 */
export function initLoginFaq(): void {
  const faqLink = document.getElementById('faq_link');
  const faqText = document.getElementById('faq_text');

  if (!faqLink || !faqText) {
    return;
  }

  faqLink.addEventListener('click', (e: Event) => {
    e.preventDefault();

    if (faqText.classList.contains('faq-hidden')) {
      faqText.classList.remove('faq-hidden');
      faqText.classList.add('faq-visible');
    } else {
      faqText.classList.remove('faq-visible');
      faqText.classList.add('faq-hidden');
    }
  });
}
