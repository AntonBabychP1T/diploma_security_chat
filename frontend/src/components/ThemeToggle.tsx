import React from 'react';
import { Moon, Sun } from 'lucide-react';
import clsx from 'clsx';
import { useTheme } from '../context/ThemeContext';

interface Props {
    compact?: boolean;
}

export const ThemeToggle: React.FC<Props> = ({ compact = false }) => {
    const { theme, setTheme } = useTheme();

    return (
        <div
            className={clsx(
                "inline-flex items-center gap-1 rounded-lg border border-gray-200 bg-white p-1 dark:border-white/10 dark:bg-gray-900/60",
                compact ? "text-xs" : "text-sm"
            )}
            title="Theme"
        >
            <button
                type="button"
                onClick={() => setTheme('dark')}
                className={clsx(
                    "flex items-center gap-1 rounded-md px-2 py-1 font-medium transition-colors",
                    theme === 'dark'
                        ? "bg-primary-600 text-white"
                        : "text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-white/5 dark:hover:text-white"
                )}
                title="Dark theme"
            >
                <Moon size={compact ? 14 : 16} />
                <span>Dark</span>
            </button>
            <button
                type="button"
                onClick={() => setTheme('light')}
                className={clsx(
                    "flex items-center gap-1 rounded-md px-2 py-1 font-medium transition-colors",
                    theme === 'light'
                        ? "bg-primary-600 text-white"
                        : "text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-white/5 dark:hover:text-white"
                )}
                title="Light theme"
            >
                <Sun size={compact ? 14 : 16} />
                <span>Light</span>
            </button>
        </div>
    );
};
