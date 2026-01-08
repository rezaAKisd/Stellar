import React from 'react';

interface Tab {
  id: string;
  label: string;
  icon?: React.ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export function Tabs({ tabs, activeTab, onTabChange }: TabsProps) {
  return (
    <div className="tabs">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`tab ${activeTab === tab.id ? 'tab--active' : ''}`}
          onClick={() => onTabChange(tab.id)}
          type="button"
        >
          {tab.icon && <span className="tab__icon">{tab.icon}</span>}
          <span className="tab__label">{tab.label}</span>
        </button>
      ))}
    </div>
  );
}
