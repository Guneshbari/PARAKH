import React from 'react';
import {
  Text,
  StyleSheet,
  Pressable,
  ViewStyle,
  TextStyle,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
import { MobileTheme, useTheme } from '../lib/theme';
import { MOBILE_SPRING_SNAPPY } from '../lib/animations';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export type ButtonVariant = 'default' | 'secondary' | 'outline' | 'ghost' | 'mint' | 'lavender';
export type ButtonSize = 'default' | 'sm' | 'pill';

interface ButtonProps {
  title: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  style?: ViewStyle;
  textStyle?: TextStyle;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export function Button({
  title,
  onPress,
  variant = 'default',
  size = 'default',
  style,
  textStyle,
  icon,
  disabled = false,
}: ButtonProps) {
  const scale = useSharedValue(1);

  let colors = MobileTheme.colors;
  try {
    const theme = useTheme();
    colors = theme.colors;
  } catch {}

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const getContainerStyle = (): ViewStyle => {
    switch (variant) {
      case 'secondary':
      case 'mint':
        return {
          backgroundColor: colors.secondaryButtonBg,
          borderColor: colors.secondaryButtonBorder,
          borderWidth: 1,
        };
      case 'outline':
      case 'lavender':
        return {
          backgroundColor: 'transparent',
          borderColor: colors.borderStrong,
          borderWidth: 1,
        };
      case 'ghost':
        return {
          backgroundColor: 'transparent',
          borderWidth: 0,
        };
      case 'default':
      default:
        return {
          backgroundColor: colors.primaryButtonBg,
          borderWidth: 0,
        };
    }
  };

  const getTextStyle = (): TextStyle => {
    switch (variant) {
      case 'secondary':
      case 'mint':
        return { color: colors.secondaryButtonText, fontWeight: '600' };
      case 'outline':
      case 'lavender':
        return { color: colors.textPrimary, fontWeight: '600' };
      case 'ghost':
        return { color: colors.textSecondary, fontWeight: '500' };
      case 'default':
      default:
        return { color: colors.primaryButtonText, fontWeight: '700' };
    }
  };

  const getSizeStyle = (): ViewStyle => {
    switch (size) {
      case 'sm':
        return { paddingVertical: 6, paddingHorizontal: 12, borderRadius: 10 };
      case 'pill':
        return { paddingVertical: 7, paddingHorizontal: 16, borderRadius: 9999 };
      default:
        return { paddingVertical: 12, paddingHorizontal: 18, borderRadius: 14 };
    }
  };

  return (
    <AnimatedPressable
      onPress={onPress}
      disabled={disabled}
      onPressIn={() => {
        scale.value = withSpring(0.96, MOBILE_SPRING_SNAPPY);
      }}
      onPressOut={() => {
        scale.value = withSpring(1, MOBILE_SPRING_SNAPPY);
      }}
      style={[
        styles.base,
        getContainerStyle(),
        getSizeStyle(),
        disabled && styles.disabled,
        animatedStyle,
        style,
      ]}
    >
      {icon}
      <Text style={[styles.text, getTextStyle(), textStyle]}>{title}</Text>
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
  },
  text: {
    fontSize: 13,
  },
  disabled: {
    opacity: 0.5,
  },
});
