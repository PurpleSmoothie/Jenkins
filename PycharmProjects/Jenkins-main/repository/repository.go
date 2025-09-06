package repository

import (
	"api/internal/model"
	"context"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/pkg/errors"
	"go.opentelemetry.io/otel"
)

type UserRepo struct {
	conn *pgxpool.Pool
}

func New(conn *pgxpool.Pool) *UserRepo {
	return &UserRepo{
		conn: conn,
	}
}

func (u *UserRepo) CreateUser(ctx context.Context, user *model.User) error {
	ctx, span := otel.Tracer("Repository").Start(ctx, "CreateUser")
	defer span.End()

	_, err := u.conn.Exec(ctx,
		"INSERT INTO users(id, name, age) VALUES ($1, $2, $3)",
		user.Id, user.Name, user.Age)
	if err != nil {
		return errors.Wrap(err, "creare user")
	}
	return nil
}

func (u *UserRepo) DeleteUser(ctx context.Context, id string) error {
	ctx, span := otel.Tracer("Repository").Start(ctx, "DeleteUser")
	defer span.End()

	_, err := u.conn.Exec(ctx, "DELETE FROM users WHERE id = $1", id)
	if err != nil {
		return errors.Wrap(err, "delete user")
	}
	return nil
}

func (u *UserRepo) UpdateUser(ctx context.Context, user *model.User) error {
	ctx, span := otel.Tracer("Repository").Start(ctx, "UpdateUser")
	defer span.End()

	_, err := u.conn.Exec(ctx,
		"UPDATE users SET name = $1, age = $2 WHERE id = $3",
		user.Name, user.Age, user.Id)
	if err != nil {
		return errors.Wrap(err, "update user")
	}
	return nil
}

func (u *UserRepo) GetUser(ctx context.Context, id string) (*model.User, error) {
	ctx, span := otel.Tracer("Repository").Start(ctx, "GetUser")
	defer span.End()

	row := u.conn.QueryRow(ctx, "SELECT id,name,age FROM users WHERE id = $1", id)
	user := model.User{}
	err := row.Scan(&user.Id, &user.Name, &user.Age)
	if errors.Is(err, pgx.ErrNoRows) {
		return &user, errors.Wrap(apperr.ErrNotFound, "not found")
	}
	if err != nil {
		return nil, errors.Wrap(err, "get user")
	}
	return &user, nil
}

func (u *UserRepo) GetUserList(ctx context.Context, limit int, offest int) (*model.Users, error) {
	ctx, span := otel.Tracer("Repository").Start(ctx, "GetUserList")
	defer span.End()

	rows, err := u.conn.Query(ctx, "SELECT id, name, age FROM users LIMIT $1 OFFSET $2", limit, offest)
	users := model.Users{}
	if err != nil {
		return nil, errors.Wrap(err, "get user list")
	}
	for rows.Next() {
		user := model.User{}
		err = rows.Scan(&user.Id, &user.Name, &user.Age)
		users.Array = append(users.Array, user)
		if err != nil {
			return nil, errors.Wrap(err, "scan rows")
		}
	}
	return &users, nil
}
