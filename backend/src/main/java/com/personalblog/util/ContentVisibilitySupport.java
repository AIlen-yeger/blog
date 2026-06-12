package com.personalblog.util;

import com.personalblog.common.BusinessException;
import com.personalblog.common.ContentStatus;
import com.personalblog.common.ErrorCode;
import com.personalblog.entity.LifeEntity;
import com.personalblog.entity.NoteEntity;
import com.personalblog.security.AdminGuard;

/** 笔记/生活记录的「仅本人可见」规则。 */
public final class ContentVisibilitySupport {

    private ContentVisibilitySupport() {
    }

    public static boolean hideOwnerOnlyFromPublic(AdminGuard adminGuard) {
        return !adminGuard.isCurrentAdmin();
    }

    public static void assertNoteReadable(NoteEntity entity, AdminGuard adminGuard) {
        if (entity == null) {
            throw new BusinessException(ErrorCode.NOTE_NOT_FOUND);
        }
        if (!adminGuard.isCurrentAdmin()) {
            if (ContentStatus.DRAFT.equals(entity.getStatus()) || entity.isOwnerOnly()) {
                throw new BusinessException(ErrorCode.NOTE_NOT_FOUND);
            }
        }
    }

    public static void assertLifeReadable(LifeEntity entity, AdminGuard adminGuard) {
        if (entity == null) {
            throw new BusinessException(ErrorCode.LIFE_NOT_FOUND);
        }
        if (!adminGuard.isCurrentAdmin()) {
            if (ContentStatus.DRAFT.equals(entity.getStatus()) || entity.isOwnerOnly()) {
                throw new BusinessException(ErrorCode.LIFE_NOT_FOUND);
            }
        }
    }
}
