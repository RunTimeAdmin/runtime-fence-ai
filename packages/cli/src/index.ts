#!/usr/bin/env node
import { Command } from 'commander';
import KillSwitchClient from '@killswitch/sdk';

const program = new Command();
const client = new KillSwitchClient({ apiUrl: process.env.KILLSWITCH_API_URL || 'http://localhost:3001' });

program.name('killswitch').description('AI Agent Kill Switch CLI').version('0.1.0');

program.command('status').description('Get system status').action(async () => {
  const status = await client.getStatus();
  console.log('Global Kill Active:', status.globalKillActive ? 'YES' : 'NO');
});

program.command('trigger').description('Trigger kill switch').option('-a, --agent <id>', 'Agent ID').option('-r, --reason <reason>', 'Reason').action(async (opts) => {
  await client.triggerKillSwitch(opts.agent, opts.reason);
  console.log('Kill switch triggered', opts.agent ? 'for ' + opts.agent : 'globally');
});

program.command('reset').description('Reset kill switch').option('-a, --agent <id>', 'Agent ID').action(async (opts) => {
  await client.resetKillSwitch(opts.agent);
  console.log('Kill switch reset', opts.agent ? 'for ' + opts.agent : 'globally');
});

program.command('agent <id>').description('Get agent status').action(async (id) => {
  const status = await client.getAgentStatus(id);
  console.log('Agent:', status.agentId, '- Status:', status.status);
});

program.parse();
