import React, { useEffect, useState } from 'react';
import { Bot, CalendarDays, Mail, Search, Sparkles } from 'lucide-react';

const steps = [
    {
        icon: Search,
        label: 'Аналізую запит',
        detail: 'Визначаю, які поштові та календарні дії потрібні.',
    },
    {
        icon: Mail,
        label: 'Перевіряю пошту',
        detail: 'Отримую релевантні листи та короткі фрагменти.',
    },
    {
        icon: CalendarDays,
        label: 'Зіставляю контекст',
        detail: 'Звіряю результати з історією розмови та календарем.',
    },
    {
        icon: Sparkles,
        label: 'Готую відповідь',
        detail: 'Формую стислий підсумок для чату.',
    },
];

export const SecretaryThinking: React.FC = () => {
    const [activeStep, setActiveStep] = useState(0);

    useEffect(() => {
        const timer = window.setInterval(() => {
            setActiveStep((current) => (current + 1) % steps.length);
        }, 1800);

        return () => window.clearInterval(timer);
    }, []);

    const ActiveIcon = steps[activeStep].icon;

    return (
        <div className="flex gap-3 sm:gap-4 max-w-4xl mx-auto w-full animate-in fade-in duration-300">
            <div className="relative mt-1 h-8 w-8 shrink-0 rounded-full bg-primary-600 text-white shadow-sm shadow-primary-900/20">
                <div className="absolute inset-0 rounded-full bg-primary-500/30 secretary-pulse-ring" />
                <div className="relative flex h-full w-full items-center justify-center rounded-full">
                    <Bot size={16} />
                </div>
            </div>

            <div className="w-full max-w-[min(34rem,85%)] overflow-hidden rounded-2xl rounded-tl-sm border border-gray-200 bg-white/90 p-4 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-gray-850/80">
                <div className="flex items-start gap-3">
                    <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-primary-500/20 bg-primary-500/10 text-primary-700 dark:border-primary-400/20 dark:text-primary-200">
                        <ActiveIcon size={19} className="secretary-icon-float" />
                        <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-primary-300 secretary-dot-pulse" />
                    </div>

                    <div className="min-w-0 flex-1">
                        <div className="mb-1 flex items-center justify-between gap-3">
                            <div className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
                                {steps[activeStep].label}
                            </div>
                            <div className="flex shrink-0 gap-1">
                                <span className="h-1.5 w-1.5 rounded-full bg-primary-300 secretary-wave-dot [animation-delay:0ms]" />
                                <span className="h-1.5 w-1.5 rounded-full bg-primary-300 secretary-wave-dot [animation-delay:160ms]" />
                                <span className="h-1.5 w-1.5 rounded-full bg-primary-300 secretary-wave-dot [animation-delay:320ms]" />
                            </div>
                        </div>
                        <div className="text-sm leading-relaxed text-gray-500 dark:text-gray-400">
                            {steps[activeStep].detail}
                        </div>
                    </div>
                </div>

                <div className="mt-4 grid grid-cols-4 gap-2">
                    {steps.map((step, index) => {
                        const StepIcon = step.icon;
                        const isActive = index === activeStep;

                        return (
                            <div
                                key={step.label}
                                className="flex h-8 items-center justify-center rounded-md border border-gray-200 bg-gray-50 dark:border-white/5 dark:bg-gray-900/70"
                                aria-hidden="true"
                            >
                                <StepIcon
                                    size={15}
                                    className={isActive ? 'text-primary-600 dark:text-primary-200' : 'text-gray-400 dark:text-gray-600'}
                                />
                            </div>
                        );
                    })}
                </div>

                <div className="mt-3 h-1 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-950/80">
                    <div className="h-full w-1/3 rounded-full bg-primary-400 secretary-progress" />
                </div>
            </div>
        </div>
    );
};
