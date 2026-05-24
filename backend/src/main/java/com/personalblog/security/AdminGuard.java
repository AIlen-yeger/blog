package com.personalblog.security;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ErrorCode;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

@Component
public class AdminGuard {

    public AuthUserPrincipal requireAuthenticated() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !(auth.getPrincipal() instanceof AuthUserPrincipal principal)) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }
        return principal;
    }

    public AuthUserPrincipal requireAdmin() {
        AuthUserPrincipal principal = requireAuthenticated();
        if (!principal.isAdmin()) {
            throw new BusinessException(ErrorCode.FORBIDDEN);
        }
        return principal;
    }

    public boolean isCurrentAdmin() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        return auth != null
                && auth.getPrincipal() instanceof AuthUserPrincipal principal
                && principal.isAdmin();
    }
}
