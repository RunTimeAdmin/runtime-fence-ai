import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View, TouchableOpacity, Linking, ScrollView } from 'react-native';

export default function App() {
  const openJupiter = () => {
    Linking.openURL('https://jup.ag/tokens/56o8um92XU8QMr1FsSj4nkExEkgKe56PBTAMqCAzmoon');
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        <StatusBar style="light" />
        
        {/* Header */}
        <Text style={styles.title}>
          <Text style={styles.killswitch}>$KILLSWITCH</Text>
        </Text>
        <Text style={styles.subtitle}>Because every AI needs an off switch.</Text>

        {/* Stats Cards */}
        <View style={styles.statsGrid}>
          <View style={styles.statCard}>
            <Text style={styles.statLabel}>Your Balance</Text>
            <Text style={styles.statValue}>0 $KILL</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statLabel}>Voting Power</Text>
            <Text style={styles.statValue}>0 votes</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statLabel}>Your Tier</Text>
            <Text style={styles.statValue}>-</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statLabel}>Discount</Text>
            <Text style={styles.statValue}>0%</Text>
          </View>
        </View>

        {/* Features */}
        <View style={styles.featureCard}>
          <Text style={styles.featureTitle}>Runtime Fence</Text>
          <Text style={styles.featureDesc}>Real-time AI agent monitoring and control</Text>
        </View>
        
        <View style={styles.featureCard}>
          <Text style={styles.featureTitle}>82/82 Tests</Text>
          <Text style={styles.featureDesc}>Production-ready with full test coverage</Text>
        </View>
        
        <View style={styles.featureCard}>
          <Text style={styles.featureTitle}>Governance</Text>
          <Text style={styles.featureDesc}>Vote on proposals with your tokens</Text>
        </View>

        {/* CTA Button */}
        <TouchableOpacity style={styles.button} onPress={openJupiter}>
          <Text style={styles.buttonText}>Buy on Jupiter</Text>
        </TouchableOpacity>

        {/* Tier Info */}
        <View style={styles.tierSection}>
          <Text style={styles.sectionTitle}>Token Holder Tiers</Text>
          <Text style={styles.tierItem}>1,000 $KILL → Vote on proposals</Text>
          <Text style={styles.tierItem}>10,000 $KILL → 10% discount</Text>
          <Text style={styles.tierItem}>100,000 $KILL → 20% discount</Text>
          <Text style={styles.tierItem}>1,000,000 $KILL → 40% + 2x votes</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  content: {
    padding: 20,
    paddingTop: 60,
  },
  title: {
    fontSize: 36,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 8,
  },
  killswitch: {
    color: '#ef4444',
  },
  subtitle: {
    fontSize: 16,
    color: '#9ca3af',
    textAlign: 'center',
    marginBottom: 32,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  statCard: {
    width: '48%',
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  statLabel: {
    color: '#9ca3af',
    fontSize: 12,
  },
  statValue: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 4,
  },
  featureCard: {
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  featureTitle: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  featureDesc: {
    color: '#9ca3af',
    fontSize: 14,
    marginTop: 4,
  },
  button: {
    backgroundColor: '#dc2626',
    borderRadius: 12,
    padding: 16,
    marginTop: 12,
    marginBottom: 24,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  tierSection: {
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  sectionTitle: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  tierItem: {
    color: '#22c55e',
    fontSize: 14,
    marginBottom: 8,
  },
});