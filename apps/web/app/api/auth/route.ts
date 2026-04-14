import { supabase } from '../../../lib/supabase';
import { NextRequest, NextResponse } from 'next/server';
import { sign, verify } from 'jsonwebtoken';

if (!process.env.NEXTAUTH_SECRET) {
  throw new Error('NEXTAUTH_SECRET must be set in environment variables');
}

const JWT_SECRET = process.env.NEXTAUTH_SECRET;

export async function POST(req: NextRequest) {
  try {
    const { walletAddress, action } = await req.json();

    if (action === 'login') {
      // Validate wallet address format
      if (!walletAddress || !/^0x[a-fA-F0-9]{40}$/.test(walletAddress)) {
        return NextResponse.json({ error: 'Invalid wallet address format' }, { status: 400 });
      }
      // Check if user exists
      let { data: user, error } = await supabase
        .from('users')
        .select('*')
        .eq('wallet_address', walletAddress)
        .single();

      // Create user if doesn't exist
      if (!user) {
        const { data: newUser, error: createError } = await supabase
          .from('users')
          .insert({
            wallet_address: walletAddress,
            tier: 'free',
            created_at: new Date().toISOString()
          })
          .select()
          .single();

        if (createError) {
          return NextResponse.json({ error: 'Failed to create user' }, { status: 500 });
        }
        user = newUser;
      }

      // Generate JWT token
      const token = sign(
        { 
          userId: user.id, 
          walletAddress,
          tier: user.tier 
        },
        JWT_SECRET,
        { expiresIn: '7d' }
      );

      return NextResponse.json({
        success: true,
        token,
        user: {
          id: user.id,
          walletAddress: user.wallet_address,
          tier: user.tier,
          createdAt: user.created_at
        }
      });
    }

    if (action === 'verify') {
      const { token } = await req.json();
      
      try {
        const decoded = verify(token, JWT_SECRET);
        return NextResponse.json({ valid: true, user: decoded });
      } catch {
        return NextResponse.json({ valid: false }, { status: 401 });
      }
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}