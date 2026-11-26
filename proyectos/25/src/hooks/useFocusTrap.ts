/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Focus Trap Hook with WCAG 2.4.3 activeElement restoration
 */

import { useEffect, RefObject } from 'react';

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

function getVisibleFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (el) => el.offsetParent !== null || el.getClientRects().length > 0
  );
}

export const useFocusTrap = (containerRef: RefObject<HTMLElement | null>, isOpen: boolean) => {
  useEffect(() => {
    if (!isOpen || !containerRef.current) return;

    const modal = containerRef.current;
    const previouslyActiveElement = document.activeElement as HTMLElement | null;

    const initialFocusables = getVisibleFocusableElements(modal);
    if (initialFocusables.length > 0) {
      initialFocusables[0].focus();
    } else if (typeof modal.focus === 'function') {
      modal.focus();
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      const focusableElements = getVisibleFocusableElements(modal);
      if (focusableElements.length === 0) {
        e.preventDefault();
        modal.focus();
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement as HTMLElement | null;
      const isInsideModal = activeElement ? modal.contains(activeElement) : false;

      if (e.shiftKey) {
        if (!isInsideModal || activeElement === firstElement || activeElement === modal) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        if (!isInsideModal || activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    modal.addEventListener('keydown', handleKeyDown);
    return () => {
      modal.removeEventListener('keydown', handleKeyDown);
      if (previouslyActiveElement && typeof previouslyActiveElement.focus === 'function') {
        previouslyActiveElement.focus();
      }
    };
  }, [isOpen, containerRef]);
};
