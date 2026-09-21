import React from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { View } from 'react-native';
import { MobileTheme } from '../lib/theme';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <View style={{ flex: 1, backgroundColor: MobileTheme.colors.background }}>
        <StatusBar style="light" backgroundColor={MobileTheme.colors.background} />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: MobileTheme.colors.background },
            animation: 'slide_from_right',
          }}
        />
      </View>
    </SafeAreaProvider>
  );
}
