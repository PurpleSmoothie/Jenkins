package repository

import (
	"api/internal/model"
	"context"
)

//go:generate mockgen -source=interface.go -destination=mock/repistory.go
type UserProvider interface {
	CreateUser(ctx context.Context, user *model.User) error
	DeleteUser(ctx context.Context, id string) error
	UpdateUser(ctx context.Context, user *model.User) error
	GetUser(ctx context.Context, id string) (*model.User, error)
	GetUserList(ctx context.Context, limit int, offest int) (*model.Users, error)
}
