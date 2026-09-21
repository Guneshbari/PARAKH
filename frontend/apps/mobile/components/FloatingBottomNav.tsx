import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { Home, FileText, Plus, BarChart3, User, LucideIcon } from 'lucide-react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
import { MobileTheme } from '../lib/theme';
import { MOBILE_SPRING_TACTILE } from '../lib/animations';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export type TabKey = 'home' | 'applications' | 'assess' | 'report' | 'profile';

interface FloatingBottomNavProps {
  activeTab: TabKey;
  onTabSelect: (tab: TabKey) => void;
  portal?: 'user' | 'admin';
}

export function FloatingBottomNav({
  activeTab,
  onTabSelect,
}: FloatingBottomNavProps) {
  const centerScale = useSharedValue(1);

  const centerAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: centerScale.value }],
  }));

  const navItems: { key: TabKey; label: string; icon: LucideIcon; isAction?: boolean }[] = [
    { key: 'home', label: 'Home', icon: Home },
    { key: 'applications', label: 'Queue', icon: FileText },
    { key: 'assess', label: 'Assess', icon: Plus, isAction: true },
    { key: 'report', label: 'Report', icon: BarChart3 },
    { key: 'profile', label: 'Profile', icon: User },
  ];

  return (
    <View style={styles.container} pointerEvents="box-none">
      <View style={styles.dock}>
        {navItems.map((item) => {
          const isActive = activeTab === item.key;
          const IconComponent = item.icon;

          if (item.isAction) {
            return (
              <AnimatedPressable
                key={item.key}
                onPress={() => onTabSelect(item.key)}
                onPressIn={() => {
                  centerScale.value = withSpring(0.92, MOBILE_SPRING_TACTILE);
                }}
                onPressOut={() => {
                  centerScale.value = withSpring(1, MOBILE_SPRING_TACTILE);
                }}
                style={[styles.actionButton, centerAnimatedStyle]}
                accessibilityRole="button"
                accessibilityLabel={item.label}
              >
                <IconComponent size={22} color="#1E1B2E" strokeWidth={2.5} />
              </AnimatedPressable>
            );
          }

          return (
            <Pressable
              key={item.key}
              onPress={() => onTabSelect(item.key)}
              style={styles.tabItem}
              accessibilityRole="tab"
              accessibilityState={{ selected: isActive }}
            >
              <IconComponent
                size={18}
                color={isActive ? MobileTheme.colors.mint : MobileTheme.colors.textSecondary}
                strokeWidth={isActive ? 2.5 : 2}
              />
              <Text
                style={[
                  styles.tabLabel,
                  {
                    color: isActive
                      ? MobileTheme.colors.mint
                      : MobileTheme.colors.textSecondary,
                  },
                ]}
              >
                {item.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 24,
    left: 0,
    right: 0,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  dock: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(20, 23, 28, 0.94)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 9999,
    paddingVertical: 8,
    paddingHorizontal: 16,
    width: '100%',
    maxWidth: 380,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 10,
  },
  tabItem: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 4,
    paddingHorizontal: 8,
    gap: 3,
  },
  tabLabel: {
    fontSize: 10,
    fontWeight: '600',
  },
  actionButton: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: MobileTheme.colors.lavender,
    alignItems: 'center',
    justifyContent: 'center',
    marginHorizontal: 4,
    shadowColor: MobileTheme.colors.lavender,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
});
