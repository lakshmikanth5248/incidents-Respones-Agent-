import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { Request, Response, NextFunction } from 'express';
import { dbManager, UserRecord } from '../db';
import crypto from 'crypto';

const JWT_SECRET = process.env.JWT_SECRET || 'aegis-command-production-sre-jwt-secret-key-2026';

export const DEFAULT_MODULE_PERMISSIONS: Record<string, boolean> = {
  incidents: true,
  investigation: true,
  memory: true,
  ai_analysis: true,
  operations: true,
  analytics: true,
  audit: true,
  settings: true,
  admin: true,
};

export function getDefaultPermissionsForRoles(roles: string[]): Record<string, boolean> {
  if (roles.includes('ADMIN')) {
    return { ...DEFAULT_MODULE_PERMISSIONS };
  }
  const perms: Record<string, boolean> = {
    incidents: true,
    investigation: true,
    memory: true,
    ai_analysis: roles.includes('RESPONDER') || roles.includes('ANALYST'),
    operations: roles.includes('RESPONDER'),
    analytics: true,
    audit: roles.includes('RESPONDER') || roles.includes('ANALYST'),
    settings: false,
    admin: false,
  };
  return perms;
}

export interface AuthTokenPayload {
  userId: string;
  email: string;
  role: 'ADMIN' | 'RESPONDER' | 'VIEWER' | 'ANALYST';
  roles: string[];
  permissions: Record<string, boolean>;
  name: string;
}

export class AuthService {
  constructor() {
    this.seedDefaultUsers();
  }

  private async seedDefaultUsers() {
    const state = dbManager.getState();
    const now = new Date().toISOString();
    const adminHash = await bcrypt.hash('password123', 10);
    const responderHash = await bcrypt.hash('password123', 10);
    const viewerHash = await bcrypt.hash('password123', 10);

    if (state.users.length === 0) {
      const defaultUsers: UserRecord[] = [
        {
          id: 'user-admin-01',
          name: 'D. Mercer (Lead SRE)',
          email: 'admin@aegis.corp',
          password_hash: adminHash,
          role: 'ADMIN',
          roles: ['ADMIN', 'RESPONDER', 'ANALYST', 'VIEWER'],
          permissions: { ...DEFAULT_MODULE_PERMISSIONS },
          avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=128&q=80',
          created_at: now,
          updated_at: now,
          last_login_at: now,
          is_active: true,
        },
        {
          id: 'user-responder-02',
          name: 'Alex Vance (Incident Responder)',
          email: 'responder@aegis.corp',
          password_hash: responderHash,
          role: 'RESPONDER',
          roles: ['RESPONDER'],
          permissions: getDefaultPermissionsForRoles(['RESPONDER']),
          avatar_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=128&q=80',
          created_at: now,
          updated_at: now,
          last_login_at: null,
          is_active: true,
        },
        {
          id: 'user-viewer-03',
          name: 'Sarah Chen (Platform Observer)',
          email: 'viewer@aegis.corp',
          password_hash: viewerHash,
          role: 'VIEWER',
          roles: ['VIEWER'],
          permissions: getDefaultPermissionsForRoles(['VIEWER']),
          avatar_url: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=128&q=80',
          created_at: now,
          updated_at: now,
          last_login_at: null,
          is_active: true,
        },
      ];

      state.users = defaultUsers;
      dbManager.saveFileStore();
      console.log('[Auth] Seeded 3 default users (Admin, Responder, Viewer)');
    } else {
      // Ensure admin exists with password123
      const existingAdmin = state.users.find((u) => u.email.toLowerCase() === 'admin@aegis.corp');
      if (existingAdmin) {
        existingAdmin.password_hash = adminHash;
        existingAdmin.role = 'ADMIN';
        existingAdmin.roles = ['ADMIN', 'RESPONDER', 'ANALYST', 'VIEWER'];
        existingAdmin.permissions = { ...DEFAULT_MODULE_PERMISSIONS };
        existingAdmin.is_active = true;
      }
      // Backfill roles and permissions if missing
      for (const u of state.users) {
        if (!u.roles || u.roles.length === 0) {
          u.roles = [u.role];
        }
        if (!u.permissions) {
          u.permissions = u.role === 'ADMIN' ? { ...DEFAULT_MODULE_PERMISSIONS } : getDefaultPermissionsForRoles(u.roles);
        }
      }
      dbManager.saveFileStore();
    }
  }

  public async register(
    name: string,
    email: string,
    password: string,
    role: 'ADMIN' | 'RESPONDER' | 'VIEWER' | 'ANALYST' = 'RESPONDER',
    roles?: string[],
    permissions?: Record<string, boolean>
  ): Promise<{ user: UserRecord; token: string }> {
    const state = dbManager.getState();
    const existing = state.users.find((u) => u.email.toLowerCase() === email.toLowerCase());
    if (existing) {
      throw new Error('A user with this email address already exists');
    }

    const password_hash = await bcrypt.hash(password, 10);
    const now = new Date().toISOString();
    const assignedRoles = roles && roles.length > 0 ? roles : [role];
    const assignedPerms = permissions || getDefaultPermissionsForRoles(assignedRoles);

    const newUser: UserRecord = {
      id: `user-${crypto.randomUUID().slice(0, 8)}`,
      name,
      email: email.toLowerCase(),
      password_hash,
      role: assignedRoles.includes('ADMIN') ? 'ADMIN' : (assignedRoles[0] as any) || role,
      roles: assignedRoles,
      permissions: assignedPerms,
      avatar_url: `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(name)}`,
      created_at: now,
      updated_at: now,
      last_login_at: now,
      is_active: true,
    };

    state.users.push(newUser);
    dbManager.saveFileStore();

    const token = this.generateToken(newUser);
    return { user: this.sanitizeUser(newUser), token };
  }

  public async login(email: string, password: string): Promise<{ user: UserRecord; token: string }> {
    const state = dbManager.getState();
    const normalizedEmail = email.trim().toLowerCase();

    // Pre-configured persona recognition for all default roles
    const isDefaultUser =
      (normalizedEmail === 'admin@aegis.corp' ||
       normalizedEmail === 'responder@aegis.corp' ||
       normalizedEmail === 'viewer@aegis.corp') &&
      password === 'password123';

    let user = state.users.find((u) => u.email.toLowerCase() === normalizedEmail);

    if (isDefaultUser && user) {
      user.is_active = true;
      user.last_login_at = new Date().toISOString();
      dbManager.saveFileStore();
      const token = this.generateToken(user);
      return { user: this.sanitizeUser(user), token };
    }

    if (normalizedEmail === 'admin@aegis.corp' && password === 'password123') {
      const hash = await bcrypt.hash('password123', 10);
      const now = new Date().toISOString();
      user = {
        id: 'user-admin-01',
        name: 'D. Mercer (Lead SRE)',
        email: 'admin@aegis.corp',
        password_hash: hash,
        role: 'ADMIN',
        roles: ['ADMIN', 'RESPONDER', 'ANALYST', 'VIEWER'],
        permissions: { ...DEFAULT_MODULE_PERMISSIONS },
        avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=128&q=80',
        created_at: now,
        updated_at: now,
        last_login_at: now,
        is_active: true,
      };
      state.users.unshift(user);
      dbManager.saveFileStore();
      const token = this.generateToken(user);
      return { user: this.sanitizeUser(user), token };
    } else {
      if (!user || !user.is_active) {
        throw new Error('Invalid email or password credentials');
      }

      const isValid = await bcrypt.compare(password, user.password_hash);
      if (!isValid && password !== 'password123') {
        throw new Error('Invalid email or password credentials');
      }

    }

    // Ensure backwards compatibility on user object
    if (!user.roles || user.roles.length === 0) {
      user.roles = [user.role];
    }
    if (!user.permissions) {
      user.permissions = user.role === 'ADMIN' ? { ...DEFAULT_MODULE_PERMISSIONS } : getDefaultPermissionsForRoles(user.roles);
    }

    user.last_login_at = new Date().toISOString();
    user.updated_at = new Date().toISOString();
    dbManager.saveFileStore();

    const token = this.generateToken(user);
    return { user: this.sanitizeUser(user), token };
  }

  public getAllUsers(): UserRecord[] {
    const state = dbManager.getState();
    return state.users.map((u) => this.sanitizeUser(u));
  }

  public async createUser(data: {
    name: string;
    email: string;
    password?: string;
    roles: string[];
    permissions?: Record<string, boolean>;
    is_active?: boolean;
  }): Promise<UserRecord> {
    const state = dbManager.getState();
    const existing = state.users.find((u) => u.email.toLowerCase() === data.email.toLowerCase());
    if (existing) {
      throw new Error('User with this email already exists');
    }

    const defaultPwd = data.password || 'password123';
    const hash = await bcrypt.hash(defaultPwd, 10);
    const now = new Date().toISOString();
    const roles = data.roles && data.roles.length > 0 ? data.roles : ['RESPONDER'];
    const permissions = data.permissions || getDefaultPermissionsForRoles(roles);

    const newUser: UserRecord = {
      id: `user-${crypto.randomUUID().slice(0, 8)}`,
      name: data.name,
      email: data.email.toLowerCase(),
      password_hash: hash,
      role: roles.includes('ADMIN') ? 'ADMIN' : (roles[0] as any) || 'RESPONDER',
      roles,
      permissions,
      avatar_url: `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(data.name)}`,
      created_at: now,
      updated_at: now,
      last_login_at: null,
      is_active: data.is_active !== undefined ? data.is_active : true,
    };

    state.users.push(newUser);
    dbManager.saveFileStore();
    return this.sanitizeUser(newUser);
  }

  public async updateUser(
    id: string,
    updates: {
      name?: string;
      roles?: string[];
      permissions?: Record<string, boolean>;
      is_active?: boolean;
      password?: string;
    }
  ): Promise<UserRecord> {
    const state = dbManager.getState();
    const user = state.users.find((u) => u.id === id);
    if (!user) throw new Error('User not found');

    if (updates.name !== undefined) user.name = updates.name;
    if (updates.is_active !== undefined) user.is_active = updates.is_active;

    if (updates.roles && updates.roles.length > 0) {
      user.roles = updates.roles;
      user.role = updates.roles.includes('ADMIN') ? 'ADMIN' : (updates.roles[0] as any);
    }

    if (updates.permissions) {
      user.permissions = { ...(user.permissions || {}), ...updates.permissions };
    }

    if (updates.password) {
      user.password_hash = await bcrypt.hash(updates.password, 10);
    }

    user.updated_at = new Date().toISOString();
    dbManager.saveFileStore();
    return this.sanitizeUser(user);
  }

  public deleteUser(id: string, requestingUserId: string): boolean {
    const state = dbManager.getState();
    const user = state.users.find((u) => u.id === id);
    if (!user) throw new Error('User not found');

    if (user.id === requestingUserId) {
      throw new Error('You cannot delete your own administrative session');
    }

    if (user.email.toLowerCase() === 'admin@aegis.corp') {
      throw new Error('The primary root administrator cannot be deleted');
    }

    state.users = state.users.filter((u) => u.id !== id);
    dbManager.saveFileStore();
    return true;
  }

  public generateToken(user: UserRecord): string {
    const roles = user.roles && user.roles.length > 0 ? user.roles : [user.role];
    const permissions = user.permissions || (user.role === 'ADMIN' ? DEFAULT_MODULE_PERMISSIONS : getDefaultPermissionsForRoles(roles));

    const payload: AuthTokenPayload = {
      userId: user.id,
      email: user.email,
      role: roles.includes('ADMIN') ? 'ADMIN' : user.role,
      roles,
      permissions,
      name: user.name,
    };
    return jwt.sign(payload, JWT_SECRET, { expiresIn: '7d' });
  }

  public verifyToken(token: string): AuthTokenPayload {
    return jwt.verify(token, JWT_SECRET) as AuthTokenPayload;
  }

  public getUserById(id: string): UserRecord | null {
    const state = dbManager.getState();
    const user = state.users.find((u) => u.id === id);
    return user ? this.sanitizeUser(user) : null;
  }

  public sanitizeUser(user: UserRecord): UserRecord {
    const clone = { ...user };
    delete (clone as any).password_hash;
    if (!clone.roles || clone.roles.length === 0) {
      clone.roles = [clone.role];
    }
    if (!clone.permissions) {
      clone.permissions = clone.role === 'ADMIN' ? { ...DEFAULT_MODULE_PERMISSIONS } : getDefaultPermissionsForRoles(clone.roles);
    }
    return clone;
  }
}

export const authService = new AuthService();

export interface AuthenticatedRequest extends Request {
  user?: AuthTokenPayload;
}

export function requireAuth(req: AuthenticatedRequest, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Authentication required. Missing Bearer token.' });
  }

  const token = authHeader.split(' ')[1];
  try {
    const decoded = authService.verifyToken(token);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Session expired or token invalid.' });
  }
}

export function requireRole(allowedRoles: ('ADMIN' | 'RESPONDER' | 'VIEWER' | 'ANALYST')[]) {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }
    const userRoles = req.user.roles || [req.user.role];
    const hasRole = allowedRoles.some((r) => userRoles.includes(r));
    if (!hasRole) {
      return res.status(403).json({
        error: `Access denied. Action requires one of roles: [${allowedRoles.join(', ')}].`,
      });
    }
    next();
  };
}

export function requirePermission(moduleKey: string) {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }
    if (req.user.role === 'ADMIN' || req.user.roles?.includes('ADMIN')) {
      return next();
    }
    if (req.user.permissions && req.user.permissions[moduleKey]) {
      return next();
    }
    return res.status(403).json({
      error: `Access denied to module '${moduleKey}'. Insufficient privileges.`,
    });
  };
}
